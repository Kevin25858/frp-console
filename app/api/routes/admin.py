"""
管理员功能的 API 路由
"""
import os
from flask import Blueprint, request, jsonify, current_app

from services.alert_service import AlertService

admin_bp = Blueprint('admin', __name__)


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


@admin_bp.route('/api/alerts', methods=['GET'])
def get_alerts():
    """获取所有告警"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    alerts = AlertService.get_all_alerts()
    return jsonify(alerts)


@admin_bp.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """标记告警为已解决"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, result = AlertService.resolve_alert(alert_id)

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@admin_bp.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    """清除已解决的告警"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    if not verify_csrf_token():
        return jsonify({'error': 'CSRF 验证失败'}), 403

    success, result = AlertService.clear_resolved_alerts()

    if success:
        return jsonify(result)
    else:
        return jsonify(result), 400


@admin_bp.route('/api/alerts/stats', methods=['GET'])
def get_alert_stats():
    """获取告警统计信息"""
    if not login_required():
        return jsonify({'error': '未登录，请先登录'}), 401

    stats = AlertService.get_alert_stats()
    return jsonify(stats)
