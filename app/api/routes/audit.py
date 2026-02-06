"""
审计日志路由
提供审计日志查询和统计功能
"""
from flask import Blueprint, jsonify, request

from services.audit_log_service import AuditLogService
from utils.decorators import login_required

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/api/audit-logs', methods=['GET'])
@login_required
def get_audit_logs():
    """获取审计日志列表"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        action = request.args.get('action')
        level = request.args.get('level')
        user = request.args.get('user')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 限制最大返回数量
        limit = min(limit, 1000)

        logs = AuditLogService.get_logs(
            limit=limit,
            action=action,
            level=level,
            user=user,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@audit_bp.route('/api/audit-logs/statistics', methods=['GET'])
@login_required
def get_audit_statistics():
    """获取审计日志统计信息"""
    try:
        days = request.args.get('days', 30, type=int)
        stats = AuditLogService.get_statistics(days=days)

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500