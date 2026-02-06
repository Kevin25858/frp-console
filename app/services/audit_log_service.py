"""
审计日志服务
记录系统的关键操作和安全事件
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from flask import request, session

from models.database import get_db_connection
from utils.logger import ColorLogger


class AuditLogService:
    """审计日志服务类"""

    # 审计日志级别
    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_ERROR = "ERROR"
    LEVEL_CRITICAL = "CRITICAL"

    # 审计操作类型
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_LOGIN_FAILED = "login_failed"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_CLIENT_CREATE = "client_create"
    ACTION_CLIENT_UPDATE = "client_update"
    ACTION_CLIENT_DELETE = "client_delete"
    ACTION_CLIENT_START = "client_start"
    ACTION_CLIENT_STOP = "client_stop"
    ACTION_CLIENT_RESTART = "client_restart"
    ACTION_CONFIG_UPDATE = "config_update"
    ACTION_ALERT_SENT = "alert_sent"

    @staticmethod
    def log(
        action: str,
        details: Optional[Dict[str, Any]] = None,
        level: str = LEVEL_INFO,
        user: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        记录审计日志

        Args:
            action: 操作类型
            details: 操作详情
            level: 日志级别
            user: 执行操作的用户ID
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            是否记录成功
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 获取用户信息
            if user is None:
                user = session.get('user_id')

            # 获取请求信息
            if ip_address is None:
                ip_address = request.remote_addr if request else 'unknown'
            if user_agent is None:
                user_agent = request.headers.get('User-Agent', 'unknown') if request else 'unknown'

            # 记录审计日志
            cursor.execute('''
                INSERT INTO audit_logs (
                    action, details, level, user_id, ip_address, user_agent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                action,
                str(details) if details else None,
                level,
                user,
                ip_address,
                user_agent,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))

            conn.commit()
            conn.close()

            # 根据级别记录到应用日志
            username = session.get('username', 'unknown')
            if level == AuditLogService.LEVEL_CRITICAL:
                ColorLogger.critical(f"[AUDIT] {action} by {username} from {ip_address}", 'Audit')
            elif level == AuditLogService.LEVEL_ERROR:
                ColorLogger.error(f"[AUDIT] {action} by {username} from {ip_address}", 'Audit')
            elif level == AuditLogService.LEVEL_WARNING:
                ColorLogger.warning(f"[AUDIT] {action} by {username} from {ip_address}", 'Audit')
            else:
                ColorLogger.info(f"[AUDIT] {action} by {username} from {ip_address}", 'Audit')

            return True

        except Exception as e:
            ColorLogger.error(f"记录审计日志失败: {e}", 'Audit')
            return False

    @staticmethod
    def get_logs(
        limit: int = 100,
        action: Optional[str] = None,
        level: Optional[str] = None,
        user: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list:
        """
        获取审计日志

        Args:
            limit: 返回数量限制
            action: 过滤操作类型
            level: 过滤日志级别
            user: 过滤用户
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            审计日志列表
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 构建查询
            query = 'SELECT * FROM audit_logs WHERE 1=1'
            params = []

            if action:
                query += ' AND action = ?'
                params.append(action)

            if level:
                query += ' AND level = ?'
                params.append(level)

            if user:
                query += ' AND user_id = ?'
                params.append(user)

            if start_date:
                query += ' AND created_at >= ?'
                params.append(start_date)

            if end_date:
                query += ' AND created_at <= ?'
                params.append(end_date)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            logs = cursor.fetchall()

            conn.close()

            return [dict(log) for log in logs]

        except Exception as e:
            ColorLogger.error(f"获取审计日志失败: {e}", 'Audit')
            return []

    @staticmethod
    def get_statistics(days: int = 30) -> Dict[str, Any]:
        """
        获取审计日志统计信息

        Args:
            days: 统计天数

        Returns:
            统计信息字典
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            start_date = datetime.now() - timedelta(days=days)
            start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')

            # 总操作数
            cursor.execute('''
                SELECT COUNT(*) as total FROM audit_logs
                WHERE created_at >= ?
            ''', (start_date_str,))
            total = cursor.fetchone()['total']

            # 按操作类型统计
            cursor.execute('''
                SELECT action, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= ?
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            ''', (start_date_str,))
            actions = cursor.fetchall()

            # 按用户统计
            cursor.execute('''
                SELECT user_id, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= ?
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT 10
            ''', (start_date_str,))
            users = cursor.fetchall()

            # 按级别统计
            cursor.execute('''
                SELECT level, COUNT(*) as count
                FROM audit_logs
                WHERE created_at >= ?
                GROUP BY level
            ''', (start_date_str,))
            levels = cursor.fetchall()

            conn.close()

            return {
                'total': total,
                'actions': [dict(row) for row in actions],
                'users': [dict(row) for row in users],
                'levels': [dict(row) for row in levels],
                'period_days': days
            }

        except Exception as e:
            ColorLogger.error(f"获取审计统计失败: {e}", 'Audit')
            return {
                'total': 0,
                'actions': [],
                'users': [],
                'levels': [],
                'period_days': days
            }

    @staticmethod
    def initialize_tables():
        """初始化审计日志表"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user_id INTEGER,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_logs_action
                ON audit_logs(action)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
                ON audit_logs(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
                ON audit_logs(created_at)
            ''')

            conn.commit()
            conn.close()

            ColorLogger.success("审计日志表初始化成功", 'Audit')

        except Exception as e:
            ColorLogger.error(f"初始化审计日志表失败: {e}", 'Audit')


# 导入 timedelta 用于日期计算
from datetime import timedelta