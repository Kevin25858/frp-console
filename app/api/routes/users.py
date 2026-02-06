"""
用户管理路由模块
提供用户管理相关的 API 接口
"""
from flask import Blueprint, request, jsonify, session

from services.user_service import UserService
from services.audit_log_service import AuditLogService
from utils.decorators import login_required, admin_required
from utils.csrf import verify_csrf_token

users_bp = Blueprint('users', __name__)


@users_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """获取所有用户列表"""
    users = UserService.get_users()
    return jsonify(users)


@users_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """创建新用户"""
    # 验证 CSRF Token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not verify_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': '无效的 CSRF Token'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'viewer')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

    result = UserService.create_user(username, password, role)

    if result['success']:
        # 记录审计日志
        AuditLogService.log(
            action='CREATE_USER',
            details=f'创建用户: {username}, 角色: {role}',
            level='INFO',
            user=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """获取单个用户信息"""
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404
    return jsonify({'success': True, 'user': user})


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """更新用户信息"""
    # 验证 CSRF Token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not verify_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': '无效的 CSRF Token'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'}), 400

    # 不能修改自己的角色（防止管理员降级自己）
    current_user_id = session.get('user_id')
    if user_id == current_user_id and 'role' in data:
        return jsonify({'success': False, 'error': '不能修改自己的角色'}), 400

    role = data.get('role')
    is_active = data.get('is_active')

    # 不能禁用自己
    if user_id == current_user_id and is_active is False:
        return jsonify({'success': False, 'error': '不能禁用自己'}), 400

    result = UserService.update_user(user_id, role=role, is_active=is_active)

    if result['success']:
        # 记录审计日志
        AuditLogService.log(
            action='UPDATE_USER',
            details=f'更新用户 ID: {user_id}, 角色: {role}, 状态: {is_active}',
            level='INFO',
            user=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return jsonify(result)
    else:
        return jsonify(result), 400


@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """删除用户"""
    # 验证 CSRF Token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not verify_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': '无效的 CSRF Token'}), 403

    # 不能删除自己
    current_user_id = session.get('user_id')
    if user_id == current_user_id:
        return jsonify({'success': False, 'error': '不能删除自己'}), 400

    result = UserService.delete_user(user_id)

    if result['success']:
        # 记录审计日志
        AuditLogService.log(
            action='DELETE_USER',
            details=f'删除用户 ID: {user_id}',
            level='WARNING',
            user=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return jsonify(result)
    else:
        return jsonify(result), 400


@users_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """重置用户密码"""
    # 验证 CSRF Token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not verify_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': '无效的 CSRF Token'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'}), 400

    new_password = data.get('new_password', '')
    if not new_password:
        return jsonify({'success': False, 'error': '新密码不能为空'}), 400

    result = UserService.reset_password(user_id, new_password)

    if result['success']:
        # 记录审计日志
        AuditLogService.log(
            action='RESET_PASSWORD',
            details=f'重置用户 ID: {user_id} 的密码',
            level='WARNING',
            user=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        return jsonify(result)
    else:
        return jsonify(result), 400


@users_bp.route('/api/users/count', methods=['GET'])
@login_required
@admin_required
def get_user_count():
    """获取用户总数"""
    count = UserService.count_users()
    return jsonify({'success': True, 'count': count})
