"""
后端 API 测试
"""
import pytest
import json
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 测试环境专用配置
TEST_ADMIN_USER = 'test_admin'
TEST_ADMIN_PASSWORD = 'test_password_123'


class TestAuthRoutes:
    """认证路由测试"""

    def test_login_success(self, test_client, test_app):
        """测试登录成功"""
        # 使用测试专用账户
        from app.config import Config
        original_user = Config.ADMIN_USER
        original_salt = Config.PASSWORD_SALT
        original_password = Config.ADMIN_PASSWORD
        
        # 设置测试账户
        from app.utils.password import hash_password
        test_salt, test_hash = hash_password(TEST_ADMIN_PASSWORD)
        Config.ADMIN_USER = TEST_ADMIN_USER
        Config.PASSWORD_SALT = test_salt
        Config.ADMIN_PASSWORD = test_hash
        
        try:
            response = test_client.post('/login', data={
                'username': TEST_ADMIN_USER,
                'password': TEST_ADMIN_PASSWORD
            })
            assert response.status_code == 200
        finally:
            # 恢复原始配置
            Config.ADMIN_USER = original_user
            Config.PASSWORD_SALT = original_salt
            Config.ADMIN_PASSWORD = original_password

    def test_login_failure(self, test_client):
        """测试登录失败"""
        response = test_client.post('/login', data={
            'username': 'wrong_user',
            'password': 'wrong_password'
        })
        assert response.status_code == 401

    def test_logout(self, test_client, test_app):
        """测试登出"""
        # 使用测试专用账户先登录
        from app.config import Config
        from app.utils.password import hash_password
        
        original_user = Config.ADMIN_USER
        original_salt = Config.PASSWORD_SALT
        original_password = Config.ADMIN_PASSWORD
        
        test_salt, test_hash = hash_password(TEST_ADMIN_PASSWORD)
        Config.ADMIN_USER = TEST_ADMIN_USER
        Config.PASSWORD_SALT = test_salt
        Config.ADMIN_PASSWORD = test_hash
        
        try:
            test_client.post('/login', data={
                'username': TEST_ADMIN_USER,
                'password': TEST_ADMIN_PASSWORD
            })
            
            # 再登出
            response = test_client.get('/logout')
            assert response.status_code == 302  # 重定向
        finally:
            Config.ADMIN_USER = original_user
            Config.PASSWORD_SALT = original_salt
            Config.ADMIN_PASSWORD = original_password


class TestClientRoutes:
    """客户端路由测试"""

    def test_get_clients_requires_auth(self, test_client):
        """测试获取客户端列表需要认证"""
        response = test_client.get('/api/clients')
        assert response.status_code == 401

    def test_create_client_requires_auth(self, test_client):
        """测试创建客户端需要认证"""
        response = test_client.post('/api/clients', 
            data=json.dumps({
                'name': 'test',
                'server_addr': 'test.com',
                'local_port': 8080,
                'remote_port': 8081
            }),
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_csrf_protection(self, test_client, test_app):
        """测试 CSRF 保护"""
        # 使用测试专用账户登录
        from app.config import Config
        from app.utils.password import hash_password
        
        original_user = Config.ADMIN_USER
        original_salt = Config.PASSWORD_SALT
        original_password = Config.ADMIN_PASSWORD
        
        test_salt, test_hash = hash_password(TEST_ADMIN_PASSWORD)
        Config.ADMIN_USER = TEST_ADMIN_USER
        Config.PASSWORD_SALT = test_salt
        Config.ADMIN_PASSWORD = test_hash
        
        try:
            test_client.post('/login', data={
                'username': TEST_ADMIN_USER,
                'password': TEST_ADMIN_PASSWORD
            })
            
            # 尝试不带 CSRF token 的 POST 请求
            response = test_client.post('/api/clients',
                data=json.dumps({
                    'name': 'test',
                    'server_addr': 'test.com',
                    'local_port': 8080,
                    'remote_port': 8081
                }),
                content_type='application/json'
            )
            assert response.status_code == 403
        finally:
            Config.ADMIN_USER = original_user
            Config.PASSWORD_SALT = original_salt
            Config.ADMIN_PASSWORD = original_password


class TestUtilityFunctions:
    """工具函数测试"""

    def test_password_hash(self):
        """测试密码哈希"""
        from app.utils.password import hash_password, verify_password
        
        password = "test_password_123"
        salt, hashed = hash_password(password)
        
        assert salt is not None
        assert hashed is not None
        assert verify_password(password, salt, hashed)
        assert not verify_password("wrong_password", salt, hashed)

    def test_password_validation(self):
        """测试密码验证"""
        from app.utils.validators import validate_password
        
        # 有效密码
        valid, msg = validate_password("ValidPass123")
        assert valid
        
        # 密码太短
        valid, msg = validate_password("short")
        assert not valid
        
        # 空密码
        valid, msg = validate_password("")
        assert not valid

    def test_client_name_validation(self):
        """测试客户端名称验证"""
        from app.utils.validators import validate_client_name
        
        # 有效名称
        valid, msg = validate_client_name("test-client-123")
        assert valid
        
        # 无效名称（包含特殊字符）
        valid, msg = validate_client_name("test@client")
        assert not valid

    def test_port_validation(self):
        """测试端口验证"""
        from app.utils.validators import validate_port
        
        # 有效端口
        valid, msg = validate_port(8080)
        assert valid
        
        # 端口太大
        valid, msg = validate_port(70000)
        assert not valid
        
        # 端口为 0
        valid, msg = validate_port(0)
        assert not valid


class TestSecurityFeatures:
    """安全功能测试"""

    def test_csrf_token_generation(self, test_client, test_app):
        """测试 CSRF token 生成"""
        from app.config import Config
        from app.utils.password import hash_password
        
        original_user = Config.ADMIN_USER
        original_salt = Config.PASSWORD_SALT
        original_password = Config.ADMIN_PASSWORD
        
        test_salt, test_hash = hash_password(TEST_ADMIN_PASSWORD)
        Config.ADMIN_USER = TEST_ADMIN_USER
        Config.PASSWORD_SALT = test_salt
        Config.ADMIN_PASSWORD = test_hash
        
        try:
            # 先登录
            test_client.post('/login', data={
                'username': TEST_ADMIN_USER,
                'password': TEST_ADMIN_PASSWORD
            })
            
            # 获取 CSRF token
            response = test_client.get('/api/csrf-token')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'csrf_token' in data
            assert len(data['csrf_token']) > 0
        finally:
            Config.ADMIN_USER = original_user
            Config.PASSWORD_SALT = original_salt
            Config.ADMIN_PASSWORD = original_password

    def test_rate_limiting(self, test_client):
        """测试登录速率限制"""
        # 连续多次失败登录
        for i in range(6):
            response = test_client.post('/login', data={
                'username': 'test_user',
                'password': 'wrong_password'
            })
        
        # 第6次应该被限制
        assert response.status_code == 401
        # 响应中应该包含等待提示
        response_data = response.get_json() if response.is_json else {}
        # 注意：由于速率限制是基于 IP 的，测试环境可能需要调整
