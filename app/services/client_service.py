"""
客户端服务模块
处理客户端的 CRUD 操作 - 纯配置管理，不管理进程
"""
import os
import re
from typing import Dict, List, Optional, Tuple

from config import Config
from utils.logger import ColorLogger
from utils.validators import validate_client_name, validate_toml_config
from models.database import get_db
from services.audit_log_service import AuditLogService


class ClientService:
    """客户端服务类 - 纯配置管理"""

    @staticmethod
    def get_all_clients() -> List[Dict]:
        """
        获取所有客户端

        Returns:
            客户端列表
        """
        db = get_db()
        clients = db.execute('SELECT * FROM clients ORDER BY id').fetchall()
        clients_list = [dict(row) for row in clients]
        return clients_list

    @staticmethod
    def get_client(client_id: int) -> Optional[Dict]:
        """
        获取单个客户端

        Args:
            client_id: 客户端 ID

        Returns:
            客户端信息，不存在则返回 None
        """
        db = get_db()
        client = db.execute(
            'SELECT * FROM clients WHERE id = ?',
            (client_id,)
        ).fetchone()
        return dict(client) if client else None

    @staticmethod
    def create_client(data: Dict) -> Tuple[bool, Dict]:
        """
        创建新客户端

        Args:
            data: 客户端数据

        Returns:
            (是否成功, 响应数据)
        """
        name = data.get('name')

        # 验证名称
        valid, message = validate_client_name(name)
        if not valid:
            return False, {'error': message}

        # 检查是否是粘贴配置模式
        if data.get('config_content'):
            config_content = data.get('config_content')

            # 验证 TOML 格式
            valid, message = validate_toml_config(config_content)
            if not valid:
                return False, {'error': message}

            # 从配置内容解析关键信息
            try:
                import tomllib
                parsed_config = tomllib.loads(config_content)

                # 获取 common 部分的配置
                common_config = parsed_config.get('common', {})
                server_addr = common_config.get('server_addr') or common_config.get('serverAddr', '127.0.0.1')
                server_port = common_config.get('server_port') or common_config.get('serverPort', 7000)

                # 获取第一个 proxy 部分的配置
                proxy_config = {}
                for key, value in parsed_config.items():
                    if key != 'common':
                        proxy_config = value
                        break

                local_port = proxy_config.get('local_port') or proxy_config.get('localPort', 0)
                remote_port = proxy_config.get('remote_port') or proxy_config.get('remotePort', 0)
            except Exception as e:
                ColorLogger.warning(f'解析 TOML 配置失败，使用正则回退: {e}', 'Client')
                # 回退到正则表达式解析
                server_addr_match = re.search(r'server_addr|serverAddr\s*=\s*["\']?([^"\'\n]+)["\']?', config_content)
                server_port_match = re.search(r'server_port|serverPort\s*=\s*(\d+)', config_content)
                local_port_match = re.search(r'local_port|localPort\s*=\s*(\d+)', config_content)
                remote_port_match = re.search(r'remote_port|remotePort\s*=\s*(\d+)', config_content)

                server_addr = server_addr_match.group(1).strip() if server_addr_match else '127.0.0.1'
                server_port = int(server_port_match.group(1)) if server_port_match else 7000
                local_port = int(local_port_match.group(1)) if local_port_match else 0
                remote_port = int(remote_port_match.group(1)) if remote_port_match else 0
        else:
            # 表单模式
            server_addr = data.get('server_addr')
            server_port = data.get('server_port', 7000)
            token = data.get('token', 'ChmlFrpToken')
            user = data.get('user', 'LrqS7A0jwRdbRAyQB6k4ikzU')
            local_port = data.get('local_port')
            remote_port = data.get('remote_port')

            # 生成配置文件
            config_content = f"""[common]
server_addr = {server_addr}
server_port = {server_port}
tls_enable = false
user = {user}
token = {token}

[proxy]
type = tcp
local_ip = 127.0.0.1
local_port = {local_port}
remote_port = {remote_port}
"""

        # 插入数据库 - 配置内容直接存储在数据库中
        db = get_db()
        cursor = db.execute('''
            INSERT INTO clients (name, config_content, local_port, remote_port, server_addr, enabled)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (name, config_content, local_port, remote_port, server_addr))
        db.commit()
        client_id = cursor.lastrowid

        ColorLogger.success(f"客户端 {name} 创建成功", 'Client')

        # 记录审计日志
        AuditLogService.log(
            AuditLogService.ACTION_CLIENT_CREATE,
            details={'client_id': client_id, 'client_name': name, 'server_addr': server_addr, 'local_port': local_port, 'remote_port': remote_port},
            level=AuditLogService.LEVEL_INFO
        )

        return True, {'id': client_id, 'message': '创建成功'}

    @staticmethod
    def update_client(client_id: int, data: Dict) -> Tuple[bool, Dict]:
        """
        更新客户端信息

        Args:
            client_id: 客户端 ID
            data: 更新数据

        Returns:
            (是否成功, 响应数据)
        """
        db = get_db()

        # 读取现有配置
        client = db.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
        if client is None:
            return False, {'error': '客户端不存在'}

        # 更新数据库
        name = data.get('name', client['name'])
        enabled = data.get('enabled', client['enabled'])

        # 如果更新了名称，验证新名称
        if name != client['name']:
            valid, message = validate_client_name(name)
            if not valid:
                return False, {'error': message}

        db.execute('''
            UPDATE clients SET name = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, enabled, client_id))
        db.commit()

        ColorLogger.info(f"客户端 {name} 更新成功", 'Client')

        # 记录审计日志
        AuditLogService.log(
            AuditLogService.ACTION_CLIENT_UPDATE,
            details={'client_id': client_id, 'client_name': name, 'enabled': enabled},
            level=AuditLogService.LEVEL_INFO
        )

        return True, {'message': '更新成功'}

    @staticmethod
    def delete_client(client_id: int) -> Tuple[bool, Dict]:
        """
        删除客户端

        Args:
            client_id: 客户端 ID

        Returns:
            (是否成功, 响应数据)
        """
        db = get_db()

        # 获取客户端信息
        client = db.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
        if client is None:
            return False, {'error': '客户端不存在'}

        # 删除数据库记录
        db.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        db.execute('DELETE FROM logs WHERE client_id = ?', (client_id,))
        db.execute('DELETE FROM alerts WHERE client_id = ?', (client_id,))
        db.commit()

        ColorLogger.success(f"客户端 {client['name']} 删除成功", 'Client')

        # 记录审计日志
        AuditLogService.log(
            AuditLogService.ACTION_CLIENT_DELETE,
            details={'client_id': client_id, 'client_name': client['name']},
            level=AuditLogService.LEVEL_INFO
        )

        return True, {'message': '删除成功'}

    @staticmethod
    def get_client_config(client_id: int) -> Tuple[bool, Dict]:
        """
        获取客户端配置文件内容

        Args:
            client_id: 客户端 ID

        Returns:
            (是否成功, 响应数据)
        """
        client = ClientService.get_client(client_id)
        if client is None:
            return False, {'error': '客户端不存在'}

        config_content = client.get('config_content', '')
        return True, {'config': config_content}

    @staticmethod
    def update_client_config(client_id: int, config_content: str) -> Tuple[bool, Dict]:
        """
        更新客户端配置文件

        Args:
            client_id: 客户端 ID
            config_content: 新配置内容

        Returns:
            (是否成功, 响应数据)
        """
        client = ClientService.get_client(client_id)
        if client is None:
            return False, {'error': '客户端不存在'}

        # 验证 TOML 格式
        valid, message = validate_toml_config(config_content)
        if not valid:
            return False, {'error': message}

        # 更新数据库中的配置
        db = get_db()
        db.execute(
            'UPDATE clients SET config_content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (config_content, client_id)
        )
        db.commit()

        ColorLogger.success(f"客户端 {client['name']} 配置更新成功", 'Client')
        return True, {'message': '配置更新成功'}
