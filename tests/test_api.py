"""
后端 API 测试
"""
import pytest
import json
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 测试环境专用配置（与 conftest 一致）
TEST_ADMIN_USER = 'test_admin'
TEST_ADMIN_PASSWORD = 'test_password_123'

# 有效的 frpc TOML 配置（新格式，含占位符会被拒绝启动，但创建/保存可用）
VALID_TOML_CONFIG = '''serverAddr = "example.com"
serverPort = 7000

[[proxies]]
name = "ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 6000
'''


class TestAuthRoutes:
    """认证路由测试"""

    def test_login_success(self, test_client):
        """测试登录成功（conftest 已用真实 hash 配置 test_admin）"""
        response = test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        assert response.status_code == 302  # 登录成功后重定向

    def test_login_failure(self, test_client):
        """测试登录失败"""
        response = test_client.post('/login', data={
            'username': 'wrong_user',
            'password': 'wrong_password'
        })
        assert response.status_code == 401

    def test_logout(self, test_client):
        """测试登出"""
        test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        response = test_client.get('/logout')
        assert response.status_code == 302  # 重定向


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
                'config_content': VALID_TOML_CONFIG,
            }),
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_csrf_protection(self, test_client):
        """测试 CSRF 保护：登录后不带 CSRF token 的 POST 应被拒绝"""
        test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        response = test_client.post('/api/clients',
            data=json.dumps({
                'name': 'test',
                'config_content': VALID_TOML_CONFIG,
            }),
            content_type='application/json'
        )
        assert response.status_code == 403

    def test_create_and_list_client(self, test_client):
        """测试创建客户端并获取列表（端到端，mock docker）"""
        test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        # 获取 CSRF token
        csrf_resp = test_client.get('/api/csrf-token')
        csrf_token = json.loads(csrf_resp.data)['csrf_token']

        # 创建客户端（粘贴模式）
        resp = test_client.post('/api/clients',
            data=json.dumps({
                'name': 'test-client-api',
                'config_content': VALID_TOML_CONFIG,
            }),
            content_type='application/json',
            headers={'X-CSRF-Token': csrf_token}
        )
        assert resp.status_code == 201
        client_id = json.loads(resp.data)['id']

        # 获取列表
        resp = test_client.get('/api/clients')
        assert resp.status_code == 200
        clients = json.loads(resp.data)
        assert any(c['id'] == client_id for c in clients)

    def test_batch_enable_requires_csrf(self, test_client):
        """测试批量启用需要 CSRF token"""
        test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        resp = test_client.post('/api/clients/batch-enable',
            data=json.dumps({'enabled': True}),
            content_type='application/json'
        )
        assert resp.status_code == 403

    def test_clear_logs_requires_csrf(self, test_client):
        """测试清空日志需要 CSRF token"""
        test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        resp = test_client.post('/api/clients/999/clear-logs',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert resp.status_code == 403


class TestUtilityFunctions:
    """工具函数测试"""

    def test_password_hash(self):
        """测试密码哈希"""
        from utils.password import hash_password, verify_password

        password = "test_password_123"
        salt, hashed = hash_password(password)

        assert salt is not None
        assert hashed is not None
        assert verify_password(password, salt, hashed)
        assert not verify_password("wrong_password", salt, hashed)

    def test_password_validation(self):
        """测试密码验证"""
        from utils.validators import validate_password

        valid, msg = validate_password("ValidPass123")
        assert valid

        valid, msg = validate_password("short")
        assert not valid

        valid, msg = validate_password("")
        assert not valid

    def test_client_name_validation(self):
        """测试客户端名称验证"""
        from utils.validators import validate_client_name

        valid, msg = validate_client_name("test-client-123")
        assert valid

        valid, msg = validate_client_name("test@client")
        assert not valid

    def test_port_validation(self):
        """测试端口验证"""
        from utils.validators import validate_port

        valid, msg = validate_port(8080)
        assert valid

        valid, msg = validate_port(70000)
        assert not valid

        valid, msg = validate_port(0)
        assert not valid


class TestSecurityFeatures:
    """安全功能测试"""

    def test_csrf_token_generation(self, test_client):
        """测试 CSRF token 生成"""
        test_client.post('/login', data={
            'username': TEST_ADMIN_USER,
            'password': TEST_ADMIN_PASSWORD
        })
        response = test_client.get('/api/csrf-token')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'csrf_token' in data
        assert len(data['csrf_token']) > 0

    def test_rate_limiting(self, test_client):
        """测试登录速率限制"""
        for _ in range(6):
            response = test_client.post('/login', data={
                'username': 'test_user',
                'password': 'wrong_password'
            })
        # 第6次应被限制（仍返回 401，但被锁定）
        assert response.status_code == 401
