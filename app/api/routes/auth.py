"""
认证相关路由
"""
from flask import Blueprint, request, jsonify, session, redirect, current_app

from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/csrf-token')
def csrf_token():
    return jsonify({'csrf_token': AuthService.get_csrf_token()})


@auth_bp.route('/api/me')
def me():
    if not AuthService.is_logged_in():
        return jsonify({'authenticated': False}), 401
    return jsonify({
        'authenticated': True,
        'username': session.get('username'),
    })


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if AuthService.is_logged_in():
        return redirect('/')

    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not data:
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

    return current_app.send_static_file('index.html')


@auth_bp.route('/logout')
def logout():
    AuthService.logout()
    return redirect('/login')


@auth_bp.route('/api/change-password', methods=['POST'])
def change_password():
    if not AuthService.is_logged_in():
        return jsonify({'error': '未登录'}), 401

    token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
    if not AuthService.verify_csrf_token(token):
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.get_json() or {}
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()

    success, message = AuthService.change_password(old_password, new_password)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400
