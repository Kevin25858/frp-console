"""
客户端管理路由
"""
from flask import Blueprint, request, jsonify

from services.client_service import ClientService
from services.process_service import ProcessService
from utils.logger import ColorLogger

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

    # 先停止进程
    ProcessService.stop_frpc(client_id)

    success, result = ClientService.delete_client(client_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>/start', methods=['POST'])
def start_client(client_id):
    """启动客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    client = ClientService.get_client(client_id)
    if client is None:
        return jsonify({'error': '客户端不存在'}), 404

    success, message = ProcessService.start_frpc(
        client_id, client['config_path'], clear_log=False
    )

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500


@clients_bp.route('/api/clients/<int:client_id>/stop', methods=['POST'])
def stop_client(client_id):
    """停止客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, message = ProcessService.stop_frpc(client_id)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500


@clients_bp.route('/api/clients/<int:client_id>/restart', methods=['POST'])
def restart_client(client_id):
    """重启客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    client = ClientService.get_client(client_id)
    if client is None:
        return jsonify({'error': '客户端不存在'}), 404

    success, message = ProcessService.restart_frpc(
        client_id, client['name'], client['config_path']
    )

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500


@clients_bp.route('/api/clients/<int:client_id>/always-on', methods=['POST'])
def update_always_on(client_id):
    """更新客户端的 always_on 状态"""
    ColorLogger.info(f"收到 always_on 更新请求: client_id={client_id}", 'API')
    
    if not login_required():
        ColorLogger.warning(f"always_on 更新失败: 未登录", 'API')
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        ColorLogger.warning(f"always_on 更新失败: CSRF 验证失败", 'API')
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.json
    ColorLogger.info(f"always_on 更新请求数据: {data}", 'API')
    always_on = data.get('always_on')

    if always_on is None:
        ColorLogger.warning(f"always_on 更新失败: 缺少 always_on 参数", 'API')
        return jsonify({'error': '缺少 always_on 参数'}), 400

    client = ClientService.get_client(client_id)
    if client is None:
        ColorLogger.warning(f"always_on 更新失败: 客户端 {client_id} 不存在", 'API')
        return jsonify({'error': '客户端不存在'}), 404

    success, result = ClientService.update_client(client_id, {'always_on': always_on})

    if success:
        ColorLogger.info(f"客户端 {client['name']} always_on 状态已更新为: {always_on}", 'API')
        return jsonify({'message': 'always_on 状态更新成功'})
    else:
        ColorLogger.error(f"always_on 更新失败: {result}", 'API')
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


@clients_bp.route('/api/clients/<int:client_id>/logs', methods=['GET'])
def get_client_logs(client_id):
    """获取客户端日志"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    success, result = ClientService.get_client_logs(client_id)

    if success:
        from utils.logger import AnsiToHtml
        # 转换 ANSI 颜色代码为 HTML
        result['logs'] = AnsiToHtml.convert(result['logs'])
        return jsonify(result)
    else:
        return jsonify(result), 400