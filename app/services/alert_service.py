"""
告警服务模块
处理告警发送和管理
"""
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Dict, List, Tuple

from config import Config
from utils.logger import ColorLogger
from models.database import get_db
from services.audit_log_service import AuditLogService


class AlertService:
    """告警服务类"""

    @staticmethod
    def send_alert(client_name: str, alert_type: str, message: str) -> bool:
        """
        发送邮件告警

        Args:
            client_name: 客户端名称
            alert_type: 告警类型
            message: 告警消息

        Returns:
            是否发送成功
        """
        # 检查 SMTP 配置
        if not Config.SMTP_CONFIG.get('password') or not Config.SMTP_CONFIG.get('host') or not Config.SMTP_CONFIG.get('user'):
            ColorLogger.warning('SMTP 未完全配置（需要 host, user, password），跳过发送告警邮件', 'Alert')
            return False

        try:
            # 构建邮件内容
            msg = MIMEText(f"""FRP 客户端告警

客户端: {client_name}
告警类型: {alert_type}
消息: {message}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

请及时检查 FRP 服务状态。""", 'plain', 'utf-8')

            msg['Subject'] = f'[FRP告警] {client_name} - {alert_type}'
            msg['From'] = Config.SMTP_CONFIG['user']
            msg['To'] = ', '.join(Config.SMTP_CONFIG['to'])

            # 发送邮件
            server = smtplib.SMTP(Config.SMTP_CONFIG['host'], Config.SMTP_CONFIG['port'])
            server.starttls()
            server.login(Config.SMTP_CONFIG['user'], Config.SMTP_CONFIG['password'])
            server.sendmail(Config.SMTP_CONFIG['user'], Config.SMTP_CONFIG['to'], msg.as_string())
            server.quit()

            # 记录告警
            db = get_db()
            db.execute('''
                INSERT INTO alerts (client_id, alert_type, message, sent_to)
                SELECT id, ?, ?, ? FROM clients WHERE name = ?
            ''', (alert_type, message, ','.join(Config.SMTP_CONFIG['to']), client_name))
            db.commit()

            ColorLogger.success(f"告警邮件已发送: {client_name} - {alert_type}", 'Alert')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_ALERT_SENT,
                details={'client_name': client_name, 'alert_type': alert_type, 'message': message},
                level=AuditLogService.LEVEL_WARNING
            )

            return True

        except Exception as e:
            ColorLogger.error(f"发送邮件失败: {e}", 'Alert')

            # 记录审计日志
            AuditLogService.log(
                AuditLogService.ACTION_ALERT_SENT,
                details={'client_name': client_name, 'alert_type': alert_type, 'error': str(e)},
                level=AuditLogService.LEVEL_ERROR
            )

            return False

    @staticmethod
    def get_all_alerts() -> List[Dict]:
        """
        获取所有告警

        Returns:
            告警列表
        """
        db = get_db()
        alerts = db.execute('''
            SELECT a.*, c.name as client_name
            FROM alerts a
            LEFT JOIN clients c ON a.client_id = c.id
            ORDER BY a.sent_at DESC
        ''').fetchall()
        return [dict(row) for row in alerts]

    @staticmethod
    def resolve_alert(alert_id: int) -> Tuple[bool, Dict]:
        """
        标记告警为已解决

        Args:
            alert_id: 告警 ID

        Returns:
            (是否成功, 响应数据)
        """
        db = get_db()
        db.execute('UPDATE alerts SET resolved = 1 WHERE id = ?', (alert_id,))
        db.commit()

        ColorLogger.info(f"告警 {alert_id} 已标记为解决", 'Alert')
        return True, {'message': '告警已解决'}

    @staticmethod
    def clear_resolved_alerts() -> Tuple[bool, Dict]:
        """
        清除已解决的告警

        Returns:
            (是否成功, 响应数据)
        """
        db = get_db()
        db.execute('DELETE FROM alerts WHERE resolved = 1')
        db.commit()

        ColorLogger.info('已清除所有已解决的告警', 'Alert')
        return True, {'message': '已清除已解决的告警'}

    @staticmethod
    def get_alert_stats() -> Dict:
        """
        获取告警统计信息

        Returns:
            统计信息
        """
        db = get_db()

        total = db.execute('SELECT COUNT(*) as count FROM alerts').fetchone()['count']
        unresolved = db.execute('SELECT COUNT(*) as count FROM alerts WHERE resolved = 0').fetchone()['count']

        # 按类型统计
        type_stats = db.execute('''
            SELECT alert_type, COUNT(*) as count
            FROM alerts
            WHERE resolved = 0
            GROUP BY alert_type
        ''').fetchall()

        return {
            'total': total,
            'unresolved': unresolved,
            'resolved': total - unresolved,
            'by_type': {row['alert_type']: row['count'] for row in type_stats}
        }