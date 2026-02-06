"""
认证服务模块
处理用户认证、登录速率限制、CSRF 保护等
"""
import os
import secrets
import hmac
from typing import Tuple, Optional, Dict, Any
from flask import session, request

from config import Config
from utils.logger import ColorLogger
from utils.helpers import check_login_rate_limit, record_login_attempt
from utils.validators import validate_password
from services.user_service import UserService


class AuthService:
    """认证服务类"""

    @staticmethod
    def get_csrf_token() -> str:
        """
        获取或生成 CSRF token

        Returns:
            CSRF token 字符串
        """
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']

    @staticmethod
    def verify_csrf_token(token: Optional[str]) -> bool:
        """
        验证 CSRF token

        Args:
            token: 要验证的 token

        Returns:
            是否验证通过
        """
        stored_token = session.get('csrf_token')
        if not stored_token or not token:
            return False
        return hmac.compare_digest(stored_token, token)

    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, str]:
        """
        用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            (是否成功, 消息)
        """
        client_ip = request.remote_addr

        # 检查速率限制
        allowed, message = check_login_rate_limit(
            client_ip,
            Config.MAX_LOGIN_ATTEMPTS,
            Config.LOGIN_LOCKOUT_TIME
        )
        if not allowed:
            return False, message

        # 验证输入
        if not username or not password:
            return False, '用户名或密码不能为空'

        # 使用 UserService 验证用户
        user = UserService.verify_user_password(username, password)

        if user:
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            session.permanent = True
            record_login_attempt(client_ip, True)
            ColorLogger.success(f"用户 {username} 登录成功", 'Auth')

            # 记录审计日志
            from services.audit_log_service import AuditLogService
            AuditLogService.log(
                AuditLogService.ACTION_LOGIN,
                details={'username': username, 'ip': client_ip, 'role': user['role']},
                level=AuditLogService.LEVEL_INFO,
                user=user['id']
            )

            return True, '登录成功'

        # 登录失败
        record_login_attempt(client_ip, False)
        ColorLogger.warning(f"登录失败: 用户名或密码错误 (IP: {client_ip})", 'Auth')

        # 记录审计日志
        from services.audit_log_service import AuditLogService
        AuditLogService.log(
            AuditLogService.ACTION_LOGIN_FAILED,
            details={'username': username, 'ip': client_ip, 'reason': 'invalid_credentials'},
            level=AuditLogService.LEVEL_WARNING,
            user=None
        )

        return False, '用户名或密码错误'

    @staticmethod
    def logout() -> None:
        """用户登出"""
        username = session.get('username', 'unknown')
        user_id = session.get('user_id')

        # 记录审计日志
        from services.audit_log_service import AuditLogService
        AuditLogService.log(
            AuditLogService.ACTION_LOGOUT,
            details={'username': username},
            level=AuditLogService.LEVEL_INFO,
            user=user_id
        )

        session.pop('logged_in', None)
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('user_role', None)
        ColorLogger.info(f"用户 {username} 登出", 'Auth')

    @staticmethod
    def is_logged_in() -> bool:
        """
        检查用户是否已登录

        Returns:
            是否已登录
        """
        return 'logged_in' in session

    @staticmethod
    def get_current_user() -> Optional[str]:
        """
        获取当前登录用户名

        Returns:
            用户名，如果未登录则返回 None
        """
        return session.get('username')

    @staticmethod
    def get_current_user_id() -> Optional[int]:
        """
        获取当前登录用户ID

        Returns:
            用户ID，如果未登录则返回 None
        """
        return session.get('user_id')

    @staticmethod
    def get_current_user_role() -> Optional[str]:
        """
        获取当前登录用户角色

        Returns:
            用户角色，如果未登录则返回 None
        """
        return session.get('user_role')

    @staticmethod
    def get_current_user_info() -> Optional[Dict[str, Any]]:
        """
        获取当前登录用户完整信息

        Returns:
            用户信息字典，如果未登录则返回 None
        """
        if not AuthService.is_logged_in():
            return None
        return {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('user_role')
        }

    @staticmethod
    def change_password(old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        修改当前登录用户的密码

        Args:
            old_password: 旧密码
            new_password: 新密码

        Returns:
            (是否成功, 消息)
        """
        user_id = AuthService.get_current_user_id()
        if not user_id:
            return False, '未登录'

        # 验证旧密码
        user = UserService.get_user_by_id(user_id)
        if not user:
            return False, '用户不存在'

        # 获取完整用户信息（包含密码）
        full_user = UserService.get_user_by_username(user['username'])
        if not full_user:
            return False, '用户不存在'

        from utils.password import verify_password
        if not verify_password(old_password, full_user['password_salt'], full_user['password_hash']):
            return False, '旧密码不正确'

        # 验证新密码
        valid, message = validate_password(new_password)
        if not valid:
            return False, message

        # 使用 UserService 重置密码
        result = UserService.reset_password(user_id, new_password)

        if result['success']:
            # 记录审计日志
            from services.audit_log_service import AuditLogService
            AuditLogService.log(
                AuditLogService.ACTION_PASSWORD_CHANGE,
                details={'username': user['username']},
                level=AuditLogService.LEVEL_INFO,
                user=user_id
            )
            return True, '密码修改成功'
        else:
            return False, result.get('error', '密码修改失败')