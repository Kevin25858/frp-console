"""
进程管理服务模块
处理 frpc 进程的启动、停止、重启等操作
"""
import os
import subprocess
import time
import socket
import shlex
import gzip
import sqlite3
from datetime import datetime, timedelta
from typing import Tuple, Optional
from contextlib import contextmanager

from config import Config
from utils.logger import ColorLogger
from utils.helpers import check_restart_limit, record_restart
from models.database import get_db, get_db_connection
from services.audit_log_service import AuditLogService


@contextmanager
def get_db_context():
    """
    数据库连接上下文管理器
    自动处理 Flask 上下文内外的数据库连接
    """
    db = None
    is_standalone = False
    try:
        try:
            db = get_db()
        except RuntimeError:
            # 不在 Flask 应用上下文中，使用独立连接
            db = get_db_connection()
            is_standalone = True
        yield db
    finally:
        if db and is_standalone:
            try:
                db.close()
            except (sqlite3.Error, AttributeError) as e:
                ColorLogger.debug(f"关闭数据库连接时出错: {e}", 'ProcessService')


class LogRotator:
    """日志轮转器"""
    
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_BACKUP_COUNT = 5  # 保留5个备份
    
    @staticmethod
    def get_rotated_log_path(log_file: str, index: int) -> str:
        """获取轮转后的日志路径"""
        if index == 0:
            return log_file
        return f"{log_file}.{index}.gz"
    
    @classmethod
    def rotate(cls, log_file: str):
        """
        执行日志轮转
        
        Args:
            log_file: 日志文件路径
        """
        if not os.path.exists(log_file):
            return
        
        # 检查文件大小
        if os.path.getsize(log_file) < cls.MAX_LOG_SIZE:
            return
        
        try:
            # 删除最旧的备份
            oldest_backup = cls.get_rotated_log_path(log_file, cls.MAX_BACKUP_COUNT)
            if os.path.exists(oldest_backup):
                os.remove(oldest_backup)
            
            # 移动现有的备份文件
            for i in range(cls.MAX_BACKUP_COUNT - 1, 0, -1):
                src = cls.get_rotated_log_path(log_file, i)
                dst = cls.get_rotated_log_path(log_file, i + 1)
                if os.path.exists(src):
                    os.rename(src, dst)
            
            # 压缩当前日志文件
            backup_file = cls.get_rotated_log_path(log_file, 1)
            with open(log_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # 清空原日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] 日志轮转完成，之前的日志已压缩到 {backup_file}\n")
            
            ColorLogger.info(f"日志轮转完成: {log_file}", 'LogRotator')
            
        except Exception as e:
            ColorLogger.error(f"日志轮转失败: {e}", 'LogRotator')


class ProcessService:
    """进程管理服务类"""

    @staticmethod
    def check_port_available(port: int) -> bool:
        """
        检查端口是否可用（未被占用）

        Args:
            port: 端口号

        Returns:
            端口是否可用
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result != 0
        except (socket.error, OSError) as e:
            ColorLogger.error(f"检查端口可用性失败: {e}", 'ProcessService')
            return False

    @staticmethod
    def get_admin_port(config_path: str) -> Optional[int]:
        """
        从配置文件中读取 admin_port

        Args:
            config_path: 配置文件路径

        Returns:
            admin_port 端口号，如果读取失败返回 None
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('admin_port'):
                        port = int(line.split('=')[1].strip())
                        return port
        except Exception as e:
            ColorLogger.error(f"读取 admin_port 失败: {e}", 'ProcessService')
        return None

    @staticmethod
    def _prepare_config_for_docker(config_path: str) -> str:
        """
        为 Docker 环境准备配置文件
        如果在容器内运行，将 127.0.0.1 替换为宿主机的 IP
        """
        # 检测是否在 Docker 容器内
        if not os.path.exists('/.dockerenv'):
            return config_path

        # 读取原始配置
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 如果配置中包含 127.0.0.1，需要替换
        if '127.0.0.1' in content or 'localhost' in content:
            # 获取宿主机 IP（Docker 默认网关）
            try:
                # 方法1: 从 /proc/net/route 获取网关
                with open('/proc/net/route', 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 3 and parts[1] == '00000000':
                            gateway_hex = parts[2]
                            # 转换十六进制 IP
                            gateway_ip = '.'.join(str(int(gateway_hex[i:i+2], 16)) for i in (6, 4, 2, 0))
                            break
                    else:
                        gateway_ip = '172.17.0.1'  # 默认 Docker 网关
            except:
                gateway_ip = '172.17.0.1'

            # 替换 127.0.0.1 和 localhost
            new_content = content.replace('127.0.0.1', gateway_ip)
            new_content = new_content.replace('localhost', gateway_ip)

            # 写入临时配置文件
            temp_config_path = config_path.replace('.toml', '.docker.toml')
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            ColorLogger.info(f'Docker 环境: 已将 127.0.0.1 替换为 {gateway_ip}', 'FRPC')
            return temp_config_path

        return config_path

    @staticmethod
    def start_frpc(client_id: int, config_path: str, clear_log: bool = False) -> Tuple[bool, str]:
        """
        启动 frpc 进程

        Args:
            client_id: 客户端 ID
            config_path: 配置文件路径
            clear_log: 是否清空日志

        Returns:
            (是否成功, 消息)
        """
        try:
            # 检查端口占用
            admin_port = ProcessService.get_admin_port(config_path)
            if admin_port and not ProcessService.check_port_available(admin_port):
                return False, f"端口 {admin_port} 已被占用，无法启动"

            # 为 Docker 环境准备配置
            actual_config_path = ProcessService._prepare_config_for_docker(config_path)

            # 日志文件路径
            log_file = f"{Config.LOGS_DIR}/frpc/client-{client_id}.log"

            # 检查并执行日志轮转（如果日志文件过大）
            if not clear_log:
                LogRotator.rotate(log_file)

            # 是否清空日志
            mode = 'w' if clear_log else 'a'

            with open(log_file, mode, encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if clear_log:
                    f.write(f"[{timestamp}] 启动 frpc (手动重启)\n")
                else:
                    f.write(f"[{timestamp}] 启动 frpc\n")
                f.flush()

            # 使用 nohup + & 后台运行，脱离父进程控制
            # 安全修复：验证路径并使用参数列表避免命令注入
            if not os.path.isfile(Config.FRPC_BINARY):
                return False, f"FRPC 二进制文件不存在: {Config.FRPC_BINARY}"
            
            # 验证 config_path 在允许的目录内（使用更严格的路径验证）
            config_path = os.path.abspath(config_path)
            allowed_dirs = [os.path.abspath(Config.CONFIGS_DIR), os.path.abspath(Config.BASE_DIR)]
            
            # 使用 os.path.commonpath 进行严格的路径验证
            try:
                config_dir = os.path.dirname(config_path)
                is_allowed = any(
                    os.path.commonpath([config_dir, allowed_dir]) == allowed_dir
                    for allowed_dir in allowed_dirs
                )
                if not is_allowed:
                    return False, "配置文件路径不在允许的目录内"
            except ValueError:
                # 路径在不同驱动器上（Windows）或其他无效情况
                return False, "配置文件路径无效"
            
            # 使用参数列表而非 shell 字符串，避免命令注入
            cmd = [
                'nohup',
                Config.FRPC_BINARY,
                '-c', actual_config_path
            ]
            
            with open(log_file, 'a', encoding='utf-8') as log_f:
                subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )

            # 更新状态（使用上下文管理器）
            with get_db_context() as db:
                db.execute("UPDATE clients SET status = 'running' WHERE id = ?", (client_id,))
                db.commit()

            ColorLogger.success(f"客户端 {client_id} 已启动 (独立运行)", 'FRPC')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_CLIENT_START,
                details={'client_id': client_id, 'config_path': config_path},
                level=AuditLogService.LEVEL_INFO
            )

            return True, "启动成功 (独立模式，不受网页关闭影响)"

        except Exception as e:
            ColorLogger.error(f"启动失败: {e}", 'FRPC')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_CLIENT_START,
                details={'client_id': client_id, 'config_path': config_path, 'error': str(e)},
                level=AuditLogService.LEVEL_ERROR
            )

            return False, str(e)

    @staticmethod
    def is_frpc_running(client_id: int, config_path: str) -> bool:
        """
        检查指定客户端的 frpc 进程是否在运行

        Args:
            client_id: 客户端 ID
            config_path: 配置文件路径

        Returns:
            是否在运行
        """
        try:
            # 方法1: 查找进程（使用配置文件名匹配，不依赖完整路径）
            import os
            config_filename = os.path.basename(config_path)
            result = subprocess.run(
                ['pgrep', '-f', f'frpc.*-c.*{config_filename}'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False

            # 方法2: 检查端口是否被监听（双重确认）
            admin_port = ProcessService.get_admin_port(config_path)
            if admin_port:
                if not ProcessService.check_port_available(admin_port):
                    # 端口被占用，进程很可能正在运行
                    return True
                else:
                    # 端口未被占用，但进程存在，可能是僵尸进程
                    return False

            return True
        except Exception as e:
            ColorLogger.error(f"检查进程状态失败: {e}", 'ProcessService')
            return False

    @staticmethod
    def batch_check_process_status(client_configs: list) -> dict:
        """
        批量检查多个客户端的进程状态
        
        优化点：通过一次 pgrep 命令获取所有 frpc 进程，
        然后批量匹配客户端配置，减少系统调用次数
        
        Args:
            client_configs: 客户端配置列表，每项为 (client_id, config_path) 元组
            
        Returns:
            dict: {client_id: is_running}
        """
        result = {client_id: False for client_id, _ in client_configs}
        
        if not client_configs:
            return result
        
        try:
            # 获取所有 frpc 进程
            pgrep_result = subprocess.run(
                ['pgrep', '-a', '-f', 'frpc.*-c'],
                capture_output=True,
                text=True
            )
            
            if pgrep_result.returncode != 0:
                # 没有 frpc 进程在运行
                return result
            
            # 解析进程列表
            running_processes = pgrep_result.stdout.strip().split('\n')
            config_to_pid = {}
            
            for process_line in running_processes:
                if not process_line:
                    continue
                parts = process_line.split()
                if len(parts) >= 2:
                    pid = parts[0]
                    cmd = ' '.join(parts[1:])
                    # 提取配置文件路径
                    if '-c' in cmd:
                        cmd_parts = cmd.split()
                        for i, part in enumerate(cmd_parts):
                            if part == '-c' and i + 1 < len(cmd_parts):
                                config_path = cmd_parts[i + 1]
                                config_to_pid[config_path] = pid
                                break
            
            # 批量检查每个客户端
            for client_id, config_path in client_configs:
                # 标准化路径用于比较
                abs_config_path = os.path.abspath(config_path)
                
                # 检查配置文件是否在运行进程列表中
                is_running = False
                for running_config, pid in config_to_pid.items():
                    if os.path.abspath(running_config) == abs_config_path:
                        is_running = True
                        break
                
                # 如果进程存在，进一步检查端口确认不是僵尸进程
                if is_running:
                    admin_port = ProcessService.get_admin_port(config_path)
                    if admin_port:
                        # 如果配置了 admin 端口，检查端口是否被占用
                        if ProcessService.check_port_available(admin_port):
                            # 端口可用但进程存在，可能是僵尸进程
                            is_running = False
                
                result[client_id] = is_running
                
        except Exception as e:
            ColorLogger.error(f"批量检查进程状态失败: {e}", 'ProcessService')
            # 出错时返回所有客户端为停止状态
            
        return result

    @staticmethod
    def stop_frpc(client_id: int) -> Tuple[bool, str]:
        """
        停止 frpc 进程

        Args:
            client_id: 客户端 ID

        Returns:
            (是否成功, 消息)
        """
        try:
            # 从数据库获取配置路径（使用上下文管理器）
            with get_db_context() as db:
                client = db.execute(
                    'SELECT config_path FROM clients WHERE id = ?',
                    (client_id,)
                ).fetchone()

                if not client:
                    return False, "客户端不存在"

                config_path = client['config_path']

                # 使用 pgrep 查找进程（使用配置文件名匹配，与 is_frpc_running 保持一致）
                import os
                config_filename = os.path.basename(config_path)
                result = subprocess.run(
                    ['pgrep', '-f', f'frpc.*-c.*{config_filename}'],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            try:
                                subprocess.run(['kill', '-TERM', pid], check=False)
                                ColorLogger.info(f"已停止进程 {pid}", 'FRPC')
                            except (subprocess.SubprocessError, FileNotFoundError) as e:
                                ColorLogger.warning(f"停止进程 {pid} 失败: {e}", 'FRPC')

                    # 等待进程终止
                    time.sleep(2)

                    # 再次检查，如果还在运行则强制终止
                    result = subprocess.run(
                        ['pgrep', '-f', f'frpc.*-c.*{config_filename}'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        for pid in result.stdout.strip().split('\n'):
                            if pid:
                                subprocess.run(['kill', '-9', pid], check=False)

                # 更新状态
                db.execute("UPDATE clients SET status = 'stopped' WHERE id = ?", (client_id,))
                db.commit()

            ColorLogger.success(f"客户端 {client_id} 已停止", 'FRPC')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_CLIENT_STOP,
                details={'client_id': client_id},
                level=AuditLogService.LEVEL_INFO
            )

            return True, "停止成功"

        except Exception as e:
            ColorLogger.error(f"停止失败: {e}", 'FRPC')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_CLIENT_STOP,
                details={'client_id': client_id, 'error': str(e)},
                level=AuditLogService.LEVEL_ERROR
            )

            return False, str(e)

    @staticmethod
    def restart_frpc(
        client_id: int,
        client_name: str,
        config_path: str,
        force: bool = False,
        clear_log: bool = False
    ) -> Tuple[bool, str]:
        """
        重启 frpc 进程

        Args:
            client_id: 客户端 ID
            client_name: 客户端名称
            config_path: 配置文件路径
            force: 是否强制重启（忽略限制）
            clear_log: 是否清空日志

        Returns:
            (是否成功, 消息)
        """
        # 检查重启频率限制
        allowed, message = check_restart_limit(
            client_id,
            Config.MAX_RESTARTS_PER_WINDOW,
            Config.RESTART_WINDOW,
            Config.RESTART_COOLDOWN,
            force
        )

        if not allowed:
            record_restart(client_id, False)
            return False, message

        # 先停止
        stop_success, _ = ProcessService.stop_frpc(client_id)
        if not stop_success:
            record_restart(client_id, False)
            return False, "停止失败"

        # 等待一下
        time.sleep(0.5)

        # 再启动
        start_success, message = ProcessService.start_frpc(client_id, config_path, clear_log)

        if start_success:
            record_restart(client_id, True)
            ColorLogger.success(f"客户端 {client_name} 重启成功", 'FRPC')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_CLIENT_RESTART,
                details={'client_id': client_id, 'client_name': client_name},
                level=AuditLogService.LEVEL_INFO
            )
        else:
            record_restart(client_id, False)

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_CLIENT_RESTART,
                details={'client_id': client_id, 'client_name': client_name, 'error': message},
                level=AuditLogService.LEVEL_ERROR
            )

        return start_success, message

    @staticmethod
    def get_client_log_path(client_id: int) -> str:
        """
        获取客户端日志文件路径

        Args:
            client_id: 客户端 ID

        Returns:
            日志文件路径
        """
        return f"{Config.LOGS_DIR}/frpc/client-{client_id}.log"