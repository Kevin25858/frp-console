"""
认证相关路由
"""
from flask import Blueprint, request, jsonify, session, redirect

from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/csrf-token')
def csrf_token():
    """获取 CSRF token"""
    return jsonify({'csrf_token': AuthService.get_csrf_token()})


@auth_bp.route('/api/me')
def me():
    """获取当前用户信息（用于认证检查）"""
    if not AuthService.is_logged_in():
        return jsonify({'authenticated': False}), 401
    return jsonify({
        'authenticated': True,
        'username': session.get('username'),
        'role': session.get('user_role')
    })


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    # 如果已登录，重定向到首页
    if AuthService.is_logged_in():
        return redirect('/')

    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not data:
            # 兼容传统表单提交（前端使用 x-www-form-urlencoded）
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
        else:
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

        success, message = AuthService.login(username, password)

        if success:
            if request.is_json:
                return jsonify({'message': message})
            return redirect('/')
        else:
            if request.is_json:
                return jsonify({'error': message}), 401
            return "Invalid username or password.", 401

    # For GET requests, serve the SPA shell
    from flask import current_app
    return current_app.send_static_file('index.html')


@auth_bp.route('/logout')
def logout():
    """用户登出"""
    AuthService.logout()
    return redirect('/login')


@auth_bp.route('/api/change-password', methods=['POST'])
def change_password():
    """修改密码"""
    # 验证登录状态
    if not AuthService.is_logged_in():
        return jsonify({'error': '未登录，请先登录'}), 401

    # 验证 CSRF token
    token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
    if not AuthService.verify_csrf_token(token):
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.get_json() or {}
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()

    success, message = AuthService.change_password(old_password, new_password)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400