"""
服务控制路由
用于控制 frpc systemd 服务
"""
import subprocess
from flask import Blueprint, jsonify

from utils.logger import ColorLogger

service_bp = Blueprint('service', __name__)


def login_required():
    """检查登录状态"""
    from services.auth_service import AuthService
    if not AuthService.is_logged_in():
        return False
    return True


@service_bp.route('/api/service/start', methods=['POST'])
def start_service():
    """启动 frpc 服务"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    try:
        result = subprocess.run(
            ['systemctl', 'start', 'frpc'],
            capture_output=True,
            text=True,
            check=True
        )
        ColorLogger.success('frpc 服务已启动', 'Service')
        return jsonify({'message': '服务启动成功'})
    except subprocess.CalledProcessError as e:
        ColorLogger.error(f'启动 frpc 服务失败: {e.stderr}', 'Service')
        return jsonify({'error': f'启动失败: {e.stderr}'}), 500


@service_bp.route('/api/service/stop', methods=['POST'])
def stop_service():
    """停止 frpc 服务"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    try:
        result = subprocess.run(
            ['systemctl', 'stop', 'frpc'],
            capture_output=True,
            text=True,
            check=True
        )
        ColorLogger.success('frpc 服务已停止', 'Service')
        return jsonify({'message': '服务停止成功'})
    except subprocess.CalledProcessError as e:
        ColorLogger.error(f'停止 frpc 服务失败: {e.stderr}', 'Service')
        return jsonify({'error': f'停止失败: {e.stderr}'}), 500


@service_bp.route('/api/service/restart', methods=['POST'])
def restart_service():
    """重启 frpc 服务"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    try:
        result = subprocess.run(
            ['systemctl', 'restart', 'frpc'],
            capture_output=True,
            text=True,
            check=True
        )
        ColorLogger.success('frpc 服务已重启', 'Service')
        return jsonify({'message': '服务重启成功'})
    except subprocess.CalledProcessError as e:
        ColorLogger.error(f'重启 frpc 服务失败: {e.stderr}', 'Service')
        return jsonify({'error': f'重启失败: {e.stderr}'}), 500


@service_bp.route('/api/service/status', methods=['GET'])
def get_service_status():
    """获取 frpc 服务状态"""
    if not login_required():
        return jsonify({'error': '未登录'}), 401

    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'frpc'],
            capture_output=True,
            text=True
        )
        is_active = result.returncode == 0
        status = 'running' if is_active else 'stopped'

        return jsonify({
            'status': status,
            'active': is_active
        })
    except Exception as e:
        ColorLogger.error(f'获取 frpc 服务状态失败: {e}', 'Service')
        return jsonify({'error': str(e)}), 500
