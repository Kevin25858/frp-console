"""
装饰器模块
"""
from functools import wraps
from flask import request, jsonify
from services.auth_service import AuthService


def login_required(f):
    """检查登录状态的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AuthService.is_logged_in():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': '未登录'}), 401
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def csrf_required(f):
    """验证 CSRF token 的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-CSRF-Token') or \
                (request.json.get('csrf_token') if request.is_json else None)
        if not AuthService.verify_csrf_token(token):
            return jsonify({'error': 'CSRF 验证失败'}), 403
        return f(*args, **kwargs)
    return decorated_function
