"""
告警服务测试模块
测试告警发送、查询、解决等功能
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open


class TestAlertService:
    """告警服务测试类"""

    def test_send_alert_smtp_not_configured(self, test_app):
        """测试 SMTP 未配置时发送告警"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            from app.config import Config
            
            # 清空 SMTP 配置
            original_config = Config.SMTP_CONFIG.copy()
            Config.SMTP_CONFIG = {'host': '', 'port': 587, 'user': '', 'password': '', 'to': []}
            
            result = AlertService.send_alert('test_client', 'offline', 'Client is offline')
            assert result is False
            
            # 恢复配置
            Config.SMTP_CONFIG = original_config

    def test_send_alert_success(self, test_app):
        """测试成功发送告警邮件"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            from app.config import Config
            
            # 设置 SMTP 配置
            original_config = Config.SMTP_CONFIG.copy()
            Config.SMTP_CONFIG = {
                'host': 'smtp.example.com',
                'port': 587,
                'user': 'alert@example.com',
                'password': 'password123',
                'to': ['admin@example.com']
            }
            
            with patch('smtplib.SMTP') as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server
                
                result = AlertService.send_alert('test_client', 'offline', 'Client is offline')
                assert result is True
                
                # 验证 SMTP 调用
                mock_smtp.assert_called_once_with('smtp.example.com', 587)
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once_with('alert@example.com', 'password123')
                mock_server.sendmail.assert_called_once()
                mock_server.quit.assert_called_once()
            
            # 恢复配置
            Config.SMTP_CONFIG = original_config

    def test_send_alert_failure(self, test_app):
        """测试发送告警邮件失败"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            from app.config import Config
            
            # 设置 SMTP 配置
            original_config = Config.SMTP_CONFIG.copy()
            Config.SMTP_CONFIG = {
                'host': 'smtp.example.com',
                'port': 587,
                'user': 'alert@example.com',
                'password': 'wrong_password',
                'to': ['admin@example.com']
            }
            
            with patch('smtplib.SMTP') as mock_smtp:
                mock_smtp.side_effect = Exception('SMTP connection failed')
                
                result = AlertService.send_alert('test_client', 'offline', 'Client is offline')
                assert result is False
            
            # 恢复配置
            Config.SMTP_CONFIG = original_config

    def test_get_all_alerts(self, test_app, test_database):
        """测试获取所有告警"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            
            # 插入测试数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    alert_type TEXT,
                    message TEXT,
                    sent_to TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )
            ''')
            cursor.execute("INSERT INTO clients (id, name) VALUES (1, 'test_client')")
            cursor.execute('''
                INSERT INTO alerts (client_id, alert_type, message, resolved)
                VALUES (1, 'offline', 'Client disconnected', 0)
            ''')
            test_database.commit()
            
            with patch('app.services.alert_service.get_db', return_value=test_database):
                alerts = AlertService.get_all_alerts()
                assert len(alerts) >= 1
                assert alerts[0]['alert_type'] == 'offline'

    def test_resolve_alert(self, test_app, test_database):
        """测试标记告警为已解决"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            
            # 插入测试数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    alert_type TEXT,
                    message TEXT,
                    sent_to TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                INSERT INTO alerts (client_id, alert_type, message, resolved)
                VALUES (1, 'offline', 'Test', 0)
            ''')
            test_database.commit()
            alert_id = cursor.lastrowid
            
            with patch('app.services.alert_service.get_db', return_value=test_database):
                success, result = AlertService.resolve_alert(alert_id)
                assert success is True
                assert '已解决' in result['message']
                
                # 验证数据库更新
                cursor.execute('SELECT resolved FROM alerts WHERE id = ?', (alert_id,))
                row = cursor.fetchone()
                assert row[0] == 1

    def test_clear_resolved_alerts(self, test_app, test_database):
        """测试清除已解决的告警"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            
            # 插入测试数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    alert_type TEXT,
                    message TEXT,
                    sent_to TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                INSERT INTO alerts (client_id, alert_type, message, resolved)
                VALUES (1, 'offline', 'Test1', 1)
            ''')
            cursor.execute('''
                INSERT INTO alerts (client_id, alert_type, message, resolved)
                VALUES (1, 'error', 'Test2', 0)
            ''')
            test_database.commit()
            
            with patch('app.services.alert_service.get_db', return_value=test_database):
                success, result = AlertService.clear_resolved_alerts()
                assert success is True
                
                # 验证已解决的告警被删除
                cursor.execute('SELECT COUNT(*) FROM alerts WHERE resolved = 1')
                count = cursor.fetchone()[0]
                assert count == 0
                
                # 验证未解决的告警仍然存在
                cursor.execute('SELECT COUNT(*) FROM alerts WHERE resolved = 0')
                count = cursor.fetchone()[0]
                assert count == 1

    def test_get_alert_stats(self, test_app, test_database):
        """测试获取告警统计信息"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            
            # 插入测试数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    alert_type TEXT,
                    message TEXT,
                    sent_to TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            # 插入不同类型的告警
            alerts_data = [
                (1, 'offline', 'Test1', 0),
                (1, 'offline', 'Test2', 0),
                (1, 'error', 'Test3', 0),
                (1, 'offline', 'Test4', 1),
            ]
            for data in alerts_data:
                cursor.execute('''
                    INSERT INTO alerts (client_id, alert_type, message, resolved)
                    VALUES (?, ?, ?, ?)
                ''', data)
            test_database.commit()
            
            with patch('app.services.alert_service.get_db', return_value=test_database):
                stats = AlertService.get_alert_stats()
                assert stats['total'] == 4
                assert stats['unresolved'] == 3
                assert stats['resolved'] == 1
                assert stats['by_type']['offline'] == 2
                assert stats['by_type']['error'] == 1


class TestAlertIntegration:
    """告警集成测试类"""

    def test_alert_workflow(self, test_app, test_database):
        """测试完整的告警流程"""
        with test_app.test_request_context():
            from app.services.alert_service import AlertService
            from app.config import Config
            
            # 设置 SMTP 配置
            original_config = Config.SMTP_CONFIG.copy()
            Config.SMTP_CONFIG = {
                'host': 'smtp.example.com',
                'port': 587,
                'user': 'alert@example.com',
                'password': 'password123',
                'to': ['admin@example.com']
            }
            
            # 创建表
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    alert_type TEXT,
                    message TEXT,
                    sent_to TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )
            ''')
            cursor.execute("INSERT INTO clients (id, name) VALUES (1, 'test_client')")
            test_database.commit()
            
            with patch('app.services.alert_service.get_db', return_value=test_database):
                with patch('smtplib.SMTP') as mock_smtp:
                    mock_server = MagicMock()
                    mock_smtp.return_value = mock_server
                    
                    # 1. 发送告警
                    result = AlertService.send_alert('test_client', 'offline', 'Test message')
                    assert result is True
                    
                    # 2. 获取告警列表
                    alerts = AlertService.get_all_alerts()
                    assert len(alerts) == 1
                    alert_id = alerts[0]['id']
                    
                    # 3. 标记为已解决
                    success, _ = AlertService.resolve_alert(alert_id)
                    assert success is True
                    
                    # 4. 获取统计
                    stats = AlertService.get_alert_stats()
                    assert stats['resolved'] == 1
                    
                    # 5. 清除已解决的告警
                    success, _ = AlertService.clear_resolved_alerts()
                    assert success is True
                    
                    # 6. 验证告警列表为空
                    alerts = AlertService.get_all_alerts()
                    assert len(alerts) == 0
            
            # 恢复配置
            Config.SMTP_CONFIG = original_config