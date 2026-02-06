"""
CSRF 保护工具模块
"""
from flask import session
import hmac
import secrets


def get_csrf_token() -> str:
    """
    获取或生成 CSRF token

    Returns:
        CSRF token 字符串
    """
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def verify_csrf_token(token: str) -> bool:
    """
    验证 CSRF token

    Args:
        token: 要验证的 token

    Returns:
        是否验证通过
    """
    if not token:
        return False
    stored_token = session.get('csrf_token')
    if not stored_token:
        return False
    return hmac.compare_digest(stored_token, token)
