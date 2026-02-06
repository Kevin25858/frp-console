"""
装饰器模块
包含常用的装饰器
"""
from functools import wraps
from flask import request, redirect, url_for, jsonify, session
from services.auth_service import AuthService


def login_required(f):
    """
    检查登录状态的装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AuthService.is_logged_in():
            if request.is_json:
                return jsonify({'success': False, 'error': '未登录'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    检查是否为管理员的装饰器
    必须在 login_required 之后使用
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_role = session.get('user_role')
        if user_role != 'admin':
            if request.is_json:
                return jsonify({'success': False, 'error': '需要管理员权限'}), 403
            return jsonify({'success': False, 'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    """
    检查用户角色的装饰器

    Args:
        allowed_roles: 允许访问的角色列表，如 ['admin', 'operator']
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                if request.is_json:
                    return jsonify({'success': False, 'error': '权限不足'}), 403
                return jsonify({'success': False, 'error': '权限不足'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator