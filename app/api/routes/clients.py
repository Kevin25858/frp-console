"""
客户端管理路由

为什么用函数包装 login_required 和 verify_csrf_token：
    Flask 的装饰器虽然能做权限校验，但本项目用函数式更直观：
      if not login_required():
          return jsonify(...), 401
    这样初学者一眼能看懂"没登录就返回 401"的流程。
    高级写法是用 @login_required 装饰器，但对初学者不友好。

为什么所有路由都返回 jsonify：
    统一返回 JSON 格式，前端解析逻辑一致。
    {message: '成功'} 或 {error: '失败原因'}
"""
import hmac
from flask import Blueprint, request, jsonify, current_app

from services.client_service import ClientService
from services.process_service import ProcessService
from utils.logger import ColorLogger
from config import Config

clients_bp = Blueprint('clients', __name__)


def verify_csrf_token():
    """验证 CSRF token，返回 True 或 False"""
    # 延迟导入避免循环依赖
    # auth_service 不依赖本模块，但本模块依赖它
    # 延迟导入让模块加载顺序更灵活
    from services.auth_service import AuthService

    # 先从请求头取
    # 前端用 fetch 时通常放在 X-CSRF-Token 头里
    token = request.headers.get('X-CSRF-Token')

    # 头里没有，从表单取
    if not token:
        token = request.form.get('csrf_token')

    # 表单里也没有，从 JSON 取
    if not token and request.is_json:
        token = request.json.get('csrf_token')

    return AuthService.verify_csrf_token(token)


def login_required():
    """检查是否登录，返回 True 或 False"""
    from services.auth_service import AuthService
    return AuthService.is_logged_in()


@clients_bp.route('/api/clients', methods=['GET'])
def get_clients():
    """获取所有客户端（合并容器实时状态）"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    # 从数据库拿客户端列表
    clients = ClientService.get_all_clients()

    # 逐个获取容器的实时状态
    # 数据库里的 status 字段是缓存的旧状态，
    # 实时状态要去查 Docker，这样才能反映容器是否真的在跑
    for c in clients:
        try:
            c['status'] = ProcessService.get_status(c['id'])
        except Exception as e:
            # 查状态失败不影响整个列表，记日志后用旧状态
            ColorLogger.warning('获取客户端 ' + str(c['id']) + ' 状态失败: ' + str(e), 'Clients')

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
        # 201 Created：资源创建成功
        # 区别于 200 OK，让前端能区分"创建"和"更新"
        return jsonify(result), 201
    # 400 Bad Request：请求参数有问题
    return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """获取单个客户端"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    # <int:client_id> 是 Flask 的路由参数语法
    # int 表示只匹配整数，非整数会 404
    client = ClientService.get_client(client_id)
    if client is None:
        # 404 Not Found：资源不存在
        return jsonify({'error': '客户端不存在'}), 404

    # 合并容器实时状态
    try:
        client['status'] = ProcessService.get_status(client_id)
    except Exception:
        pass

    return jsonify(client)


@clients_bp.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    """更新客户端信息"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401
    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.json
    success, result = ClientService.update_client(client_id, data)
    if success:
        return jsonify(result)
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
    return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>/config', methods=['GET'])
def get_client_config(client_id):
    """获取客户端配置"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    success, result = ClientService.get_client_config(client_id)
    if success:
        return jsonify(result)
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
    return jsonify(result), 400


@clients_bp.route('/api/clients/<int:client_id>/status', methods=['GET'])
def get_client_status(client_id):
    """获取客户端容器实时状态"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401
    return jsonify({'status': ProcessService.get_status(client_id)})


@clients_bp.route('/api/configs/<int:client_id>/export', methods=['GET'])
def export_client_config(client_id):
    """
    导出客户端配置（供 frpc 拉取），需 API Token 认证

    为什么用 Bearer Token 而不是 session：
        这个接口是给 frpc 客户端调用的，不是给浏览器用。
        frpc 没有 cookie/session 概念，只能用 token 认证。
        Bearer Token 是 API 认证的标准做法。
    """
    # 从请求头获取 Bearer Token
    # 格式：Authorization: Bearer <token>
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': '缺少认证信息'}), 401

    # 去掉 'Bearer ' 前缀，取实际的 token
    # 'Bearer abc123'[7:] = 'abc123'
    token = auth_header[7:]

    # 验证 token
    if not Config.API_TOKEN:
        # 没配置 API_TOKEN 就禁用这个功能
        return jsonify({'error': '认证失败'}), 401
    # 用 hmac.compare_digest 防止时序攻击（见 auth_service 的说明）
    if not hmac.compare_digest(token, Config.API_TOKEN):
        return jsonify({'error': '认证失败'}), 401

    # 获取配置内容
    success, result = ClientService.get_client_config(client_id)
    if not success:
        return jsonify(result), 404

    config_content = result.get('config', '')
    # 返回纯文本而不是 JSON
    # 因为 frpc 期望拿到原始 TOML 配置，不要包一层 JSON
    return current_app.response_class(
        config_content,
        mimetype='text/plain; charset=utf-8'
    )


@clients_bp.route('/api/clients/batch-enable', methods=['POST'])
def batch_enable():
    """批量启用或禁用所有客户端"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401
    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.json or {}
    enabled = bool(data.get('enabled', False))

    clients = ClientService.get_all_clients()
    failed = []

    # 遍历所有客户端，逐个启动或停止
    for c in clients:
        if enabled:
            ok, _ = ProcessService.start(c['id'])
        else:
            ok, _ = ProcessService.stop(c['id'])

        if not ok:
            failed.append(c['name'])

        # 同步 enabled 字段到数据库
        # 这样列表页的"启用/禁用"状态和实际容器状态一致
        ClientService.update_client(c['id'], {'enabled': enabled})

    if failed:
        # 部分失败也返回 200，让前端显示具体哪些失败
        return jsonify({'message': '部分客户端操作失败: ' + ', '.join(failed)}), 200

    if enabled:
        return jsonify({'message': '启用全部'})
    return jsonify({'message': '禁用全部'})


@clients_bp.route('/api/clients/<int:client_id>/start', methods=['POST'])
def start_client(client_id):
    """启动单个客户端容器"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401
    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, message = ProcessService.start(client_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400


@clients_bp.route('/api/clients/<int:client_id>/stop', methods=['POST'])
def stop_client(client_id):
    """停止单个客户端容器"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401
    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, message = ProcessService.stop(client_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400


@clients_bp.route('/api/clients/<int:client_id>/restart', methods=['POST'])
def restart_client(client_id):
    """重启单个客户端容器"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401
    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, message = ProcessService.restart(client_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400


@clients_bp.route('/api/clients/<int:client_id>/logs', methods=['GET'])
def get_client_logs(client_id):
    """获取单个客户端的容器日志"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    # 获取要读取的日志行数
    # 从查询参数 ?lines=500 取，默认 1000 行
    try:
        lines = int(request.args.get('lines', 1000))
    except (TypeError, ValueError):
        # 参数不是数字就用默认值
        lines = 1000

    try:
        logs = ProcessService.get_logs(client_id, lines=lines)
        return jsonify({'logs': logs})
    except Exception as e:
        ColorLogger.error('读取客户端 ' + str(client_id) + ' 日志失败: ' + str(e), 'Clients')
        # 500 Internal Server Error：服务器内部错误
        return jsonify({'error': '读取日志失败'}), 500


@clients_bp.route('/api/clients/<int:client_id>/clear-logs', methods=['POST'])
def clear_client_logs(client_id):
    """清空客户端容器日志"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401
    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, message = ProcessService.clear_logs(client_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400
