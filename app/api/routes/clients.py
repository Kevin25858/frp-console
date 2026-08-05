"""
客户端管理路由
"""
import os
import hmac
from flask import Blueprint, request, jsonify, current_app

from services.client_service import ClientService
from services.process_service import ConfigService
from utils.logger import ColorLogger
from utils.log_rotator import ClientLogManager
from config import Config

clients_bp = Blueprint('clients', __name__)


def verify_csrf_token():
    """验证 CSRF token"""
    from services.auth_service import AuthService
    token = request.headers.get('X-CSRF-Token') or \
            request.form.get('csrf_token') or \
            (request.json.get('csrf_token') if request.is_json else None)
    if not AuthService.verify_csrf_token(token):
        return False
    return True


def login_required():
    """检查登录状态"""
    from services.auth_service import AuthService
    if not AuthService.is_logged_in():
        if request.is_json:
            return False
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    return True


@clients_bp.route('/api/clients', methods=['GET'])
def get_clients():
    """获取所有客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    clients = ClientService.get_all_clients()
    return jsonify(clients)


@clients_bp.route('/api/clients', methods=['POST'])
def create_client():
    """创建新客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.json
    success, result = ClientService.create_client(data)

    if success:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """获取单个客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    client = ClientService.get_client(client_id)
    if client is None:
        return jsonify({'error': '客户端不存在'}), 404
    return jsonify(client)


@clients_bp.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    """更新客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.json
    success, result = ClientService.update_client(client_id, data)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """删除客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, result = ClientService.delete_client(client_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>/config', methods=['GET'])
def get_client_config(client_id):
    """获取客户端配置"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    success, result = ClientService.get_client_config(client_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>/config', methods=['PUT'])
def update_client_config(client_id):
    """更新客户端配置"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.json
    config_content = data.get('config', '')

    success, result = ClientService.update_client_config(client_id, config_content)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@clients_bp.route('/api/configs/<int:client_id>/export', methods=['GET'])
def export_client_config(client_id):
    """
    导出客户端配置（供 frpc 拉取）
    需要 API Token 认证
    """
    # 验证 API Token
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': '缺少认证信息'}), 401

    token = auth_header[7:]  # 移除 "Bearer "
    # 使用 hmac.compare_digest 防止时序攻击
    if not Config.API_TOKEN or not hmac.compare_digest(token, Config.API_TOKEN):
        return jsonify({'error': '认证失败'}), 401

    # 获取客户端配置
    success, result = ClientService.get_client_config(client_id)

    if not success:
        return jsonify(result), 404

    # 返回纯文本配置（不是 JSON）
    config_content = result.get('config', '')

    response = current_app.response_class(
        config_content,
        mimetype='text/plain; charset=utf-8'
    )
    return response


@clients_bp.route('/api/clients/<int:client_id>/start', methods=['POST'])
def start_client(client_id):
    """启动单个客户端"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    from services.process_manager_service import ProcessManagerService
    success, message = ProcessManagerService.start_client(client_id)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400


@clients_bp.route('/api/clients/<int:client_id>/stop', methods=['POST'])
def stop_client(client_id):
    """停止单个客户端"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    from services.process_manager_service import ProcessManagerService
    success, message = ProcessManagerService.stop_client(client_id)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400


@clients_bp.route('/api/clients/<int:client_id>/restart', methods=['POST'])
def restart_client(client_id):
    """重启单个客户端"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    from services.process_manager_service import ProcessManagerService
    success, message = ProcessManagerService.restart_client(client_id)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400


@clients_bp.route('/api/clients/<int:client_id>/logs', methods=['GET'])
def get_client_logs(client_id):
    """获取单个客户端的日志"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    try:
        # 使用 ClientLogManager 读取日志（支持日志轮转）
        logs = ClientLogManager.read_log(client_id, lines=1000)
        return jsonify({'logs': logs})
    except Exception as e:
        ColorLogger.error(f'读取客户端 {client_id} 日志失败: {e}', 'Clients')
        return jsonify({'error': '读取日志失败'}), 500

