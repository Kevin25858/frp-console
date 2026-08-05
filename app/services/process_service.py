"""
进程服务模块
通过 D-Bus (busctl) 管理宿主机上的 frpc 客户端进程
"""
import os
import re
import subprocess
from typing import Tuple

from utils.logger import ColorLogger
from models.database import get_db

CONFIGS_DIR = '/etc/frp-client'
SYSTEMD_DEST = 'org.freedesktop.systemd1'
SYSTEMD_PATH = '/org/freedesktop/systemd1'
SYSTEMD_MGR = 'org.freedesktop.systemd1.Manager'
SYSTEMD_UNIT = 'org.freedesktop.systemd1.Unit'


class ProcessService:
    """进程服务类 - 通过 D-Bus 管理宿主机上的 frpc 实例"""

    @staticmethod
    def _run_cmd(cmd: list[str], timeout: int = 10) -> Tuple[int, str, str]:
        """执行命令并返回 (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, '', '命令超时'
        except Exception as e:
            return -1, '', str(e)

    @staticmethod
    def _unit_path(client_id: int) -> str:
        """生成 systemd unit 的 D-Bus 对象路径
        busctl 编码: @ -> _40, - -> _2d, . -> _2e
        """
        name = f'frpc-console@{client_id}.service'
        encoded = name.replace('-', '_2d').replace('.', '_2e').replace('@', '_40')
        return f'/org/freedesktop/systemd1/unit/{encoded}'

    @staticmethod
    def _unit_action(client_id: int, action: str) -> Tuple[int, str, str]:
        """通过 D-Bus 调用 systemd Manager 的 StartUnit/StopUnit/RestartUnit"""
        unit_name = f'frpc-console@{client_id}.service'
        method = {'start': 'StartUnit', 'stop': 'StopUnit', 'restart': 'RestartUnit'}[action]
        return ProcessService._run_cmd([
            'sudo', 'busctl', 'call',
            SYSTEMD_DEST, SYSTEMD_PATH, SYSTEMD_MGR,
            method, 'ss', unit_name, 'replace'
        ])

    @staticmethod
    def start(client_id: int) -> Tuple[bool, str]:
        """启动客户端进程"""
        # 先 enable 确保服务可用
        unit_name = f'frpc-console@{client_id}.service'
        ProcessService._run_cmd([
            'sudo', 'busctl', 'call',
            SYSTEMD_DEST, SYSTEMD_PATH, SYSTEMD_MGR,
            'EnableUnitFiles', 'asb', '1', unit_name, '0'
        ])
        code, out, err = ProcessService._unit_action(client_id, 'start')
        if code == 0:
            ColorLogger.success(f"客户端 {client_id} 已启动", 'Process')
            return True, '启动成功'
        ColorLogger.warning(f"客户端 {client_id} 启动失败: {err}", 'Process')
        return False, f'启动失败: {err}'

    @staticmethod
    def stop(client_id: int) -> Tuple[bool, str]:
        """停止客户端进程"""
        code, out, err = ProcessService._unit_action(client_id, 'stop')
        if code == 0:
            ColorLogger.success(f"客户端 {client_id} 已停止", 'Process')
            return True, '停止成功'
        ColorLogger.warning(f"客户端 {client_id} 停止失败: {err}", 'Process')
        return False, f'停止失败: {err}'

    @staticmethod
    def restart(client_id: int) -> Tuple[bool, str]:
        """重启客户端进程"""
        code, out, err = ProcessService._unit_action(client_id, 'restart')
        if code == 0:
            ColorLogger.success(f"客户端 {client_id} 已重启", 'Process')
            return True, '重启成功'
        ColorLogger.warning(f"客户端 {client_id} 重启失败: {err}", 'Process')
        return False, f'重启失败: {err}'

    @staticmethod
    def get_status(client_id: int) -> str:
        """获取客户端进程状态: running / stopped / error"""
        unit_path = ProcessService._unit_path(client_id)
        code, out, err = ProcessService._run_cmd([
            'sudo', 'busctl', 'get-property',
            SYSTEMD_DEST, unit_path, SYSTEMD_UNIT, 'ActiveState'
        ])
        if code == 0:
            # 输出格式: s "active" 或 s "inactive"
            match = re.search(r'"(\w+)"', out)
            if match:
                state = match.group(1)
                if state == 'active':
                    return 'running'
                elif state == 'failed':
                    return 'error'
        return 'stopped'

    @staticmethod
    def get_logs(client_id: int, lines: int = 100) -> str:
        """获取客户端进程日志"""
        service = f'frpc-console@{client_id}.service'
        code, out, err = ProcessService._run_cmd(
            ['journalctl', '-u', service, '-n', str(lines), '--no-pager'],
            timeout=15
        )
        if code == 0 and out:
            return out
        return f'日志暂无记录（服务可能尚未启动）。可在宿主机执行: journalctl -u {service} -f'

    @staticmethod
    def clear_logs(client_id: int) -> Tuple[bool, str]:
        """清空客户端进程日志（通过 rotate + vacuum 实现）"""
        service = f'frpc-console@{client_id}.service'
        # 先 rotate 创建新的 journal 文件
        code, _, err = ProcessService._run_cmd(
            ['sudo', 'journalctl', '--rotate', '-u', service],
            timeout=10
        )
        if code != 0:
            return False, f'清空日志失败: {err}'
        # vacuum 清除旧数据
        code, _, err = ProcessService._run_cmd(
            ['sudo', 'journalctl', '--vacuum-time=1s', '-u', service],
            timeout=10
        )
        if code != 0:
            return False, f'清空日志失败: {err}'
        ColorLogger.info(f"客户端 {client_id} 日志已清空", 'Process')
        return True, '日志已清空'

    @staticmethod
    def deploy_config(client_id: int) -> bool:
        """将数据库中的配置写入 /etc/frp-client/frpc-{id}.toml"""
        db = get_db()
        client = db.execute(
            'SELECT config_content FROM clients WHERE id = ?', (client_id,)
        ).fetchone()
        if not client:
            return False

        config_path = os.path.join(CONFIGS_DIR, f'frpc-{client_id}.toml')
        try:
            os.makedirs(CONFIGS_DIR, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(client['config_content'])
            ColorLogger.info(f"客户端 {client_id} 配置已部署到 {config_path}", 'Process')
            return True
        except Exception as e:
            ColorLogger.error(f"部署配置失败: {e}", 'Process')
            return False

    @staticmethod
    def remove_config(client_id: int) -> bool:
        """删除 /etc/frp-client/frpc-{id}.toml"""
        config_path = os.path.join(CONFIGS_DIR, f'frpc-{client_id}.toml')
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
                ColorLogger.info(f"客户端 {client_id} 配置文件已删除", 'Process')
            return True
        except Exception as e:
            ColorLogger.error(f"删除配置文件失败: {e}", 'Process')
            return False
