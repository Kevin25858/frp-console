"""
审计日志服务测试模块
测试审计日志记录、查询、统计等功能
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestAuditLogService:
    """审计日志服务测试类"""

    def test_log_success(self, test_app, test_database):
        """测试成功记录审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建审计日志表
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    result = AuditLogService.log(
                        action=AuditLogService.ACTION_LOGIN,
                        details={'username': 'test_user'},
                        level=AuditLogService.LEVEL_INFO,
                        user='test_user'
                    )
                    assert result is True

    def test_log_with_request_context(self, test_app, test_database):
        """测试在请求上下文中记录审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            from flask import request, session
            
            # 创建审计日志表
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            test_database.commit()
            
            # 设置 session
            with test_app.test_client() as client:
                with client.session_transaction() as sess:
                    sess['username'] = 'test_user'
                
                with patch('app.services.audit_log_service.Config') as mock_config:
                    mock_config.DATABASE = ':memory:'
                    
                    with patch('sqlite3.connect', return_value=test_database):
                        result = AuditLogService.log(
                            action=AuditLogService.ACTION_LOGOUT,
                            level=AuditLogService.LEVEL_INFO
                        )
                        assert result is True

    def test_get_logs_all(self, test_app, test_database):
        """测试获取所有审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建表并插入数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入测试数据
            logs_data = [
                ('login', 'INFO', 'user1', '192.168.1.1'),
                ('logout', 'INFO', 'user1', '192.168.1.1'),
                ('client_create', 'INFO', 'user2', '192.168.1.2'),
                ('login_failed', 'WARNING', 'user3', '192.168.1.3'),
            ]
            for action, level, user, ip in logs_data:
                cursor.execute('''
                    INSERT INTO audit_logs (action, level, user, ip_address, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                ''', (action, level, user, ip))
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    logs = AuditLogService.get_logs(limit=10)
                    assert len(logs) == 4

    def test_get_logs_filtered_by_action(self, test_app, test_database):
        """测试按操作类型过滤审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建表并插入数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入测试数据
            logs_data = [
                ('login', 'INFO', 'user1'),
                ('login', 'INFO', 'user2'),
                ('logout', 'INFO', 'user1'),
            ]
            for action, level, user in logs_data:
                cursor.execute('''
                    INSERT INTO audit_logs (action, level, user, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (action, level, user))
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    logs = AuditLogService.get_logs(action='login', limit=10)
                    assert len(logs) == 2
                    for log in logs:
                        assert log['action'] == 'login'

    def test_get_logs_filtered_by_level(self, test_app, test_database):
        """测试按日志级别过滤审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建表并插入数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入测试数据
            logs_data = [
                ('login', 'INFO', 'user1'),
                ('login_failed', 'WARNING', 'user2'),
                ('error', 'ERROR', 'user3'),
            ]
            for action, level, user in logs_data:
                cursor.execute('''
                    INSERT INTO audit_logs (action, level, user, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (action, level, user))
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    logs = AuditLogService.get_logs(level='WARNING', limit=10)
                    assert len(logs) == 1
                    assert logs[0]['level'] == 'WARNING'

    def test_get_logs_filtered_by_user(self, test_app, test_database):
        """测试按用户过滤审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建表并插入数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入测试数据
            logs_data = [
                ('login', 'INFO', 'user1'),
                ('logout', 'INFO', 'user1'),
                ('login', 'INFO', 'user2'),
            ]
            for action, level, user in logs_data:
                cursor.execute('''
                    INSERT INTO audit_logs (action, level, user, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (action, level, user))
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    logs = AuditLogService.get_logs(user='user1', limit=10)
                    assert len(logs) == 2
                    for log in logs:
                        assert log['user'] == 'user1'

    def test_get_logs_with_date_range(self, test_app, test_database):
        """测试按日期范围过滤审计日志"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建表并插入数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入不同日期的数据
            cursor.execute('''
                INSERT INTO audit_logs (action, level, user, created_at)
                VALUES ('login', 'INFO', 'user1', '2026-01-01 10:00:00')
            ''')
            cursor.execute('''
                INSERT INTO audit_logs (action, level, user, created_at)
                VALUES ('login', 'INFO', 'user2', '2026-02-01 10:00:00')
            ''')
            cursor.execute('''
                INSERT INTO audit_logs (action, level, user, created_at)
                VALUES ('login', 'INFO', 'user3', '2026-03-01 10:00:00')
            ''')
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    logs = AuditLogService.get_logs(
                        start_date='2026-02-01 00:00:00',
                        end_date='2026-02-28 23:59:59',
                        limit=10
                    )
                    assert len(logs) == 1
                    assert logs[0]['user'] == 'user2'

    def test_get_statistics(self, test_app, test_database):
        """测试获取审计日志统计信息"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            # 创建表并插入数据
            cursor = test_database.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    user TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入测试数据
            logs_data = [
                ('login', 'INFO', 'user1'),
                ('login', 'INFO', 'user2'),
                ('logout', 'INFO', 'user1'),
                ('client_create', 'INFO', 'user1'),
                ('login_failed', 'WARNING', 'user3'),
            ]
            for action, level, user in logs_data:
                cursor.execute('''
                    INSERT INTO audit_logs (action, level, user, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (action, level, user))
            test_database.commit()
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    stats = AuditLogService.get_statistics(days=30)
                    assert stats['total'] == 5
                    assert len(stats['actions']) == 4  # login, logout, client_create, login_failed
                    assert len(stats['users']) == 3  # user1, user2, user3
                    assert len(stats['levels']) == 2  # INFO, WARNING

    def test_initialize_tables(self, test_app, test_database):
        """测试初始化审计日志表"""
        with test_app.test_request_context():
            from app.services.audit_log_service import AuditLogService
            
            with patch('app.services.audit_log_service.Config') as mock_config:
                mock_config.DATABASE = ':memory:'
                
                with patch('sqlite3.connect', return_value=test_database):
                    AuditLogService.initialize_tables()
                    
                    # 验证表是否创建
                    cursor = test_database.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
                    result = cursor.fetchone()
                    assert result is not None
                    
                    # 验证索引是否创建
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_audit_logs%'")
                    indexes = cursor.fetchall()
                    assert len(indexes) >= 3  # action, user, created_at 索引


class TestAuditLogActions:
    """审计日志操作类型测试类"""

    def test_action_constants(self):
        """测试审计日志操作类型常量"""
        from app.services.audit_log_service import AuditLogService
        
        assert AuditLogService.ACTION_LOGIN == 'login'
        assert AuditLogService.ACTION_LOGOUT == 'logout'
        assert AuditLogService.ACTION_LOGIN_FAILED == 'login_failed'
        assert AuditLogService.ACTION_PASSWORD_CHANGE == 'password_change'
        assert AuditLogService.ACTION_CLIENT_CREATE == 'client_create'
        assert AuditLogService.ACTION_CLIENT_UPDATE == 'client_update'
        assert AuditLogService.ACTION_CLIENT_DELETE == 'client_delete'
        assert AuditLogService.ACTION_CLIENT_START == 'client_start'
        assert AuditLogService.ACTION_CLIENT_STOP == 'client_stop'
        assert AuditLogService.ACTION_CLIENT_RESTART == 'client_restart'
        assert AuditLogService.ACTION_CONFIG_UPDATE == 'config_update'
        assert AuditLogService.ACTION_ALERT_SENT == 'alert_sent'

    def test_level_constants(self):
        """测试审计日志级别常量"""
        from app.services.audit_log_service import AuditLogService
        
        assert AuditLogService.LEVEL_INFO == 'INFO'
        assert AuditLogService.LEVEL_WARNING == 'WARNING'
        assert AuditLogService.LEVEL_ERROR == 'ERROR'
        assert AuditLogService.LEVEL_CRITICAL == 'CRITICAL'