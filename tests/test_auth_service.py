"""
认证服务测试模块
测试认证相关的功能：登录、登出、CSRF保护、密码修改等
"""
import pytest
import secrets
import hmac
from unittest.mock import patch, MagicMock


class TestAuthService:
    """认证服务测试类"""

    def test_get_csrf_token_generates_new_token(self, test_app):
        """测试生成新的 CSRF token"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            token = AuthService.get_csrf_token()
            assert token is not None
            assert len(token) > 0
            
            # 再次获取应该返回相同的 token
            token2 = AuthService.get_csrf_token()
            assert token == token2

    def test_verify_csrf_token_valid(self, test_app):
        """测试验证有效的 CSRF token"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            token = AuthService.get_csrf_token()
            assert AuthService.verify_csrf_token(token) is True

    def test_verify_csrf_token_invalid(self, test_app):
        """测试验证无效的 CSRF token"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            # 先生成一个 token
            AuthService.get_csrf_token()
            
            # 验证错误的 token
            assert AuthService.verify_csrf_token('invalid_token') is False

    def test_verify_csrf_token_empty(self, test_app):
        """测试验证空的 CSRF token"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            assert AuthService.verify_csrf_token('') is False
            assert AuthService.verify_csrf_token(None) is False

    def test_login_success(self, test_app, test_client):
        """测试成功登录"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            from app.config import Config
            from utils.password import hash_password
            
            # 设置测试密码
            test_password = 'Test123!'
            salt, hashed = hash_password(test_password)
            Config.ADMIN_USER = 'admin'
            Config.PASSWORD_SALT = salt
            Config.ADMIN_PASSWORD = hashed
            
            with test_client.session_transaction() as sess:
                pass
            
            with patch('app.services.auth_service.request') as mock_request:
                mock_request.remote_addr = '127.0.0.1'
                
                success, message = AuthService.login('admin', test_password)
                assert success is True
                assert message == '登录成功'

    def test_login_wrong_password(self, test_app):
        """测试错误密码登录"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            from app.config import Config
            from utils.password import hash_password
            
            # 设置测试密码
            test_password = 'Test123!'
            salt, hashed = hash_password(test_password)
            Config.ADMIN_USER = 'admin'
            Config.PASSWORD_SALT = salt
            Config.ADMIN_PASSWORD = hashed
            
            with patch('app.services.auth_service.request') as mock_request:
                mock_request.remote_addr = '127.0.0.1'
                
                success, message = AuthService.login('admin', 'wrong_password')
                assert success is False
                assert '用户名或密码错误' in message

    def test_login_empty_credentials(self, test_app):
        """测试空凭据登录"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            with patch('app.services.auth_service.request') as mock_request:
                mock_request.remote_addr = '127.0.0.1'
                
                # 空用户名
                success, message = AuthService.login('', 'password')
                assert success is False
                assert '不能为空' in message
                
                # 空密码
                success, message = AuthService.login('admin', '')
                assert success is False
                assert '不能为空' in message

    def test_login_rate_limit(self, test_app):
        """测试登录速率限制"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            from app.config import Config
            from utils.password import hash_password
            
            # 设置测试密码
            test_password = 'Test123!'
            salt, hashed = hash_password(test_password)
            Config.ADMIN_USER = 'admin'
            Config.PASSWORD_SALT = salt
            Config.ADMIN_PASSWORD = hashed
            Config.MAX_LOGIN_ATTEMPTS = 3
            Config.LOGIN_LOCKOUT_TIME = 900
            
            with patch('app.services.auth_service.request') as mock_request:
                mock_request.remote_addr = '192.168.1.1'
                
                # 连续失败3次
                for i in range(3):
                    success, _ = AuthService.login('admin', 'wrong_password')
                    assert success is False
                
                # 第4次应该被锁定
                success, message = AuthService.login('admin', test_password)
                assert success is False
                assert '登录失败次数过多' in message

    def test_logout(self, test_app):
        """测试登出功能"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            # 先登录
            with patch('app.services.auth_service.request') as mock_request:
                mock_request.remote_addr = '127.0.0.1'
                
                from app.config import Config
                from utils.password import hash_password
                test_password = 'Test123!'
                salt, hashed = hash_password(test_password)
                Config.ADMIN_USER = 'admin'
                Config.PASSWORD_SALT = salt
                Config.ADMIN_PASSWORD = hashed
                
                AuthService.login('admin', test_password)
                assert AuthService.is_logged_in() is True
                
                # 登出
                AuthService.logout()
                assert AuthService.is_logged_in() is False

    def test_is_logged_in(self, test_app):
        """测试登录状态检查"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            # 未登录状态
            assert AuthService.is_logged_in() is False
            
            # 模拟已登录
            from flask import session
            session['logged_in'] = True
            assert AuthService.is_logged_in() is True

    def test_get_current_user(self, test_app):
        """测试获取当前用户"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            # 未登录状态
            assert AuthService.get_current_user() is None
            
            # 模拟已登录
            from flask import session
            session['username'] = 'test_user'
            assert AuthService.get_current_user() == 'test_user'

    def test_change_password_success(self, test_app, tmp_path):
        """测试成功修改密码"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            from app.config import Config
            from utils.password import hash_password
            
            # 设置初始密码
            old_password = 'OldPass123!'
            new_password = 'NewPass123!'
            salt, hashed = hash_password(old_password)
            Config.ADMIN_USER = 'admin'
            Config.PASSWORD_SALT = salt
            Config.ADMIN_PASSWORD = hashed
            Config.CONFIG_FILE = str(tmp_path / 'test.conf')
            
            # 模拟已登录
            from flask import session
            session['username'] = 'admin'
            
            success, message = AuthService.change_password(old_password, new_password)
            assert success is True
            assert '密码修改成功' in message

    def test_change_password_wrong_old_password(self, test_app):
        """测试旧密码错误"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            from app.config import Config
            from utils.password import hash_password
            
            # 设置初始密码
            old_password = 'OldPass123!'
            salt, hashed = hash_password(old_password)
            Config.PASSWORD_SALT = salt
            Config.ADMIN_PASSWORD = hashed
            
            success, message = AuthService.change_password('wrong_password', 'NewPass123!')
            assert success is False
            assert '旧密码不正确' in message

    def test_change_password_weak_password(self, test_app):
        """测试弱密码被拒绝"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            from app.config import Config
            from utils.password import hash_password
            
            # 设置初始密码
            old_password = 'OldPass123!'
            salt, hashed = hash_password(old_password)
            Config.PASSWORD_SALT = salt
            Config.ADMIN_PASSWORD = hashed
            
            # 尝试设置弱密码
            success, message = AuthService.change_password(old_password, 'weak')
            assert success is False

    def test_change_password_env_var_set(self, test_app):
        """测试环境变量设置密码时无法修改"""
        with test_app.test_request_context():
            from app.services.auth_service import AuthService
            
            with patch.dict('os.environ', {'ADMIN_PASSWORD': 'some_password'}):
                success, message = AuthService.change_password('old', 'NewPass123!')
                assert success is False
                assert '环境变量' in message


class TestAuthIntegration:
    """认证集成测试类"""

    def test_login_logout_flow(self, test_client):
        """测试完整的登录登出流程"""
        from app.config import Config
        from utils.password import hash_password
        
        # 设置测试密码
        test_password = 'Test123!'
        salt, hashed = hash_password(test_password)
        Config.ADMIN_USER = 'admin'
        Config.PASSWORD_SALT = salt
        Config.ADMIN_PASSWORD = hashed
        
        # 访问登录页面
        response = test_client.get('/login')
        assert response.status_code == 200
        
        # 登录
        response = test_client.post('/login', data={
            'username': 'admin',
            'password': test_password
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 访问需要登录的页面
        response = test_client.get('/')
        assert response.status_code == 200
        
        # 登出
        response = test_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # 登出后访问需要登录的页面应该被重定向
        response = test_client.get('/')
        assert response.status_code == 302  # 重定向到登录页

    def test_protected_routes_redirect(self, test_client):
        """测试未登录时访问受保护路由被重定向"""
        # 未登录访问首页
        response = test_client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location
        
        # 未登录访问API
        response = test_client.get('/api/clients')
        assert response.status_code == 401  # API 返回 401

    def test_csrf_protection(self, test_client):
        """测试 CSRF 保护"""
        from app.config import Config
        from utils.password import hash_password
        
        # 设置测试密码
        test_password = 'Test123!'
        salt, hashed = hash_password(test_password)
        Config.ADMIN_USER = 'admin'
        Config.PASSWORD_SALT = salt
        Config.ADMIN_PASSWORD = hashed
        
        # 获取 CSRF token
        response = test_client.get('/api/csrf-token')
        assert response.status_code == 200
        csrf_token = response.json['csrf_token']
        
        # 使用正确的 CSRF token 登录
        response = test_client.post('/login', data={
            'username': 'admin',
            'password': test_password,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200


class TestPasswordValidation:
    """密码验证测试类"""

    def test_password_validation_strong(self):
        """测试强密码验证通过"""
        from utils.validators import validate_password
        
        valid_passwords = [
            'StrongPass123!',
            'MyP@ssw0rd',
            'C0mplex!Pass',
            'A1b2C3d4E5f6!',
        ]
        
        for password in valid_passwords:
            valid, message = validate_password(password)
            assert valid is True, f"Password '{password}' should be valid: {message}"

    def test_password_validation_weak(self):
        """测试弱密码验证失败"""
        from utils.validators import validate_password
        
        weak_passwords = [
            ('short', '太短'),
            ('onlylowercase', '大写字母'),
            ('ONLYUPPERCASE', '小写字母'),
            ('NoDigits!', '数字'),
            ('12345678', '字母'),
        ]
        
        for password, expected_error in weak_passwords:
            valid, message = validate_password(password)
            assert valid is False, f"Password '{password}' should be invalid"
            assert expected_error in message

    def test_password_validation_edge_cases(self):
        """测试密码验证边界情况"""
        from utils.validators import validate_password
        
        # 空密码
        valid, message = validate_password('')
        assert valid is False
        
        # 刚好8位且符合要求
        valid, message = validate_password('Pass123!')
        assert valid is True
        
        # 7位（不符合最小长度）
        valid, message = validate_password('Pass12!')
        assert valid is False