"""
认证服务模块
单用户认证、CSRF 保护
"""
import secrets
import hmac
from typing import Tuple, Optional, Dict, Any
from flask import session, request

from config import Config
from utils.logger import ColorLogger
from utils.helpers import check_login_rate_limit, record_login_attempt
from utils.validators import validate_password


class AuthService:
    """认证服务类 - 单用户模式"""

    @staticmethod
    def get_csrf_token() -> str:
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']

    @staticmethod
    def verify_csrf_token(token: Optional[str]) -> bool:
        stored_token = session.get('csrf_token')
        if not stored_token or not token:
            return False
        return hmac.compare_digest(stored_token, token)

    @staticmethod
    def login(username: str, password: str) -> Tuple[bool, str]:
        client_ip = request.remote_addr

        allowed, message = check_login_rate_limit(
            client_ip, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME
        )
        if not allowed:
            return False, message

        if not username or not password:
            return False, '用户名或密码不能为空'

        # 单用户验证：直接比较用户名和密码
        if username != Config.ADMIN_USER:
            record_login_attempt(client_ip, False, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME)
            ColorLogger.warning(f"登录失败: 用户名错误 (IP: {client_ip})", 'Auth')
            return False, '用户名或密码错误'

        from utils.password import verify_password
        if not verify_password(password, Config.PASSWORD_SALT, Config.ADMIN_PASSWORD):
            record_login_attempt(client_ip, False, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME)
            ColorLogger.warning(f"登录失败: 密码错误 (IP: {client_ip})", 'Auth')
            return False, '用户名或密码错误'

        session['logged_in'] = True
        session['username'] = username
        session.permanent = True
        record_login_attempt(client_ip, True, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME)
        ColorLogger.success(f"用户 {username} 登录成功", 'Auth')
        return True, '登录成功'

    @staticmethod
    def logout() -> None:
        username = session.get('username', 'unknown')
        session.pop('logged_in', None)
        session.pop('username', None)
        ColorLogger.info(f"用户 {username} 登出", 'Auth')

    @staticmethod
    def is_logged_in() -> bool:
        return 'logged_in' in session

    @staticmethod
    def get_current_user() -> Optional[str]:
        return session.get('username')

    @staticmethod
    def change_password(old_password: str, new_password: str) -> Tuple[bool, str]:
        if not AuthService.is_logged_in():
            return False, '未登录'

        from utils.password import verify_password, hash_password
        if not verify_password(old_password, Config.PASSWORD_SALT, Config.ADMIN_PASSWORD):
            return False, '旧密码不正确'

        valid, message = validate_password(new_password)
        if not valid:
            return False, message

        # 更新密码
        salt, password_hash = hash_password(new_password)
        Config.PASSWORD_SALT = salt
        Config.ADMIN_PASSWORD = password_hash
        ColorLogger.info('密码修改成功', 'Auth')
        return True, '密码修改成功'
