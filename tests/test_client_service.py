"""
客户端服务测试
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.client_service import ClientService
from services.process_service import ProcessService
from utils.validators import validate_client_name, validate_toml_config, validate_port

# 新格式 frpc TOML（顶层 serverAddr/serverPort + [[proxies]]）
VALID_TOML_CONFIG = '''serverAddr = "test.example.com"
serverPort = 7000

[[proxies]]
name = "ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8080
remotePort = 9090
'''


class TestClientNameValidation:
    """客户端名称验证测试"""

    def test_valid_client_name(self):
        """测试有效的客户端名称"""
        valid_names = [
            "test-client",
            "test_client",
            "TestClient123",
            "测试客户端",
            "test-client-123",
        ]
        for name in valid_names:
            valid, message = validate_client_name(name)
            assert valid, f"名称 '{name}' 应该有效，但返回: {message}"

    def test_invalid_client_name_special_chars(self):
        """测试包含特殊字符的无效名称"""
        invalid_names = [
            "test@client",
            "test/client",
            "test..client",
            "test client",
            "test<client>",
        ]
        for name in invalid_names:
            valid, message = validate_client_name(name)
            assert not valid, f"名称 '{name}' 应该无效"

    def test_empty_client_name(self):
        """测试空名称无效"""
        valid, message = validate_client_name("")
        assert not valid
        assert "不能为空" in message

    def test_long_client_name(self):
        """测试过长的名称无效"""
        long_name = "a" * 101
        valid, message = validate_client_name(long_name)
        assert not valid
        assert "不能超过" in message


class TestTomlConfigValidation:
    """TOML 配置验证测试"""

    def test_valid_toml_config(self):
        """测试有效的新格式 TOML 配置"""
        valid, message = validate_toml_config(VALID_TOML_CONFIG)
        assert valid, f"配置应该有效，但返回: {message}"

    def test_empty_config(self):
        """测试空配置无效"""
        valid, message = validate_toml_config("")
        assert not valid
        assert "不能为空" in message

    def test_config_without_proxy(self):
        """测试没有代理规则的配置无效"""
        config = '''
serverAddr = "127.0.0.1"
serverPort = 7000
'''
        valid, message = validate_toml_config(config)
        assert not valid
        assert "代理" in message or "proxy" in message.lower()

    def test_config_with_comments(self):
        """测试带注释的配置有效"""
        config = '''
# FRP 客户端配置
serverAddr = "127.0.0.1"
serverPort = 7000

# SSH 代理
[[proxies]]
name = "ssh"
type = "tcp"
localPort = 22
remotePort = 6000
'''
        valid, message = validate_toml_config(config)
        assert valid, f"配置应该有效，但返回: {message}"


class TestPortValidation:
    """端口验证测试"""

    def test_valid_ports(self):
        """测试有效端口"""
        valid_ports = [1, 80, 8080, 65535]
        for port in valid_ports:
            valid, message = validate_port(port)
            assert valid, f"端口 {port} 应该有效"

    def test_invalid_ports(self):
        """测试无效端口"""
        invalid_ports = [0, -1, 65536, 100000]
        for port in invalid_ports:
            valid, message = validate_port(port)
            assert not valid, f"端口 {port} 应该无效"

    def test_non_integer_port(self):
        """测试非整数端口无效"""
        valid, message = validate_port("8080")
        assert not valid
        assert "整数" in message


class TestClientService:
    """客户端服务测试"""

    def test_create_client_validation(self, test_app):
        """测试创建客户端时的名称验证"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'invalid@name',
                'config_content': VALID_TOML_CONFIG,
            })
            assert not success
            assert 'error' in result

    def test_create_client_with_config_content(self, test_app):
        """测试使用粘贴配置创建客户端"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'test-client-paste',
                'config_content': VALID_TOML_CONFIG,
            })
            assert success, f"创建应成功，但返回: {result}"
            assert 'id' in result
            # 验证字段解析
            client = ClientService.get_client(result['id'])
            assert client is not None
            assert client['server_addr'] == 'test.example.com'
            assert client['local_port'] == 8080
            assert client['remote_port'] == 9090

    def test_create_client_with_form_generation(self, test_app):
        """测试表单生成模式创建客户端"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'test-client-form',
                'server_addr': 'form.example.com',
                'server_port': 7000,
                'token': 'mytoken',
                'user': 'myuser',
                'proxy_name': 'web',
                'local_port': 3000,
                'remote_port': 3001,
            })
            assert success, f"表单生成应成功，但返回: {result}"
            assert 'id' in result
            client = ClientService.get_client(result['id'])
            assert client is not None
            assert client['server_addr'] == 'form.example.com'
            assert client['local_port'] == 3000
            assert client['remote_port'] == 3001
            # 验证生成的 TOML 包含关键内容
            assert 'serverAddr = "form.example.com"' in client['config_content']
            assert '[[proxies]]' in client['config_content']
            assert 'remotePort = 3001' in client['config_content']

    def test_create_client_with_frp_version(self, test_app):
        """测试创建客户端时指定 frp_version"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'test-client-version',
                'config_content': VALID_TOML_CONFIG,
                'frp_version': 'v0.60.0',
            })
            assert success
            client = ClientService.get_client(result['id'])
            assert client['frp_version'] == 'v0.60.0'

    def test_get_client_nonexistent(self, test_app):
        """测试获取不存在的客户端返回 None"""
        with test_app.app_context():
            client = ClientService.get_client(99999)
            assert client is None

    def test_delete_client(self, test_app):
        """测试删除客户端（mock docker 不应报错）"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'test-client-delete',
                'config_content': VALID_TOML_CONFIG,
            })
            assert success
            client_id = result['id']
            success, _ = ClientService.delete_client(client_id)
            assert success
            assert ClientService.get_client(client_id) is None


class TestProcessService:
    """进程服务测试（mock docker）"""

    def test_check_placeholders(self):
        """测试占位符校验"""
        ok, found = ProcessService.check_placeholders('serverAddr = "your-server-address"')
        assert not ok
        assert 'your-server-address' in found

        ok, found = ProcessService.check_placeholders('serverAddr = "real.example.com"')
        assert ok
        assert found == []

    def test_start_with_placeholders_rejected(self, test_app):
        """测试含占位符的配置启动被拒绝"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'test-placeholder',
                'config_content': 'serverAddr = "your-server-address"\nserverPort = 7000\n\n[[proxies]]\nname = "p"\ntype = "tcp"\nlocalPort = 1\nremotePort = 2\n',
            })
            assert success
            client_id = result['id']
            ok, msg = ProcessService.start(client_id)
            assert not ok
            assert '占位符' in msg

    def test_start_stop_with_mock_docker(self, test_app, mock_docker):
        """测试启动/停止客户端容器（mock docker）"""
        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'test-mock-docker',
                'config_content': VALID_TOML_CONFIG,
                'frp_version': 'v0.61.1',
            })
            assert success
            client_id = result['id']

            # 启动
            ok, msg = ProcessService.start(client_id)
            assert ok, f"启动应成功: {msg}"
            # 验证 mock docker 收到了 run 调用
            assert len(mock_docker.containers.run_calls) == 1
            assert mock_docker.containers.run_calls[0]['name'] == f'FRPC-test-mock-docker'
            assert 'v0.61.1' in mock_docker.containers.run_calls[0]['image']
            # 验证状态为 running
            assert ProcessService.get_status(client_id) == 'running'

            # 停止
            ok, msg = ProcessService.stop(client_id)
            assert ok
            assert ProcessService.get_status(client_id) == 'stopped'

    def test_get_logs_no_container(self, test_app):
        """测试获取不存在容器的日志"""
        with test_app.app_context():
            logs = ProcessService.get_logs(99999)
            assert '日志暂无记录' in logs or 'docker logs' in logs

    def test_needs_restart(self, test_app, mock_docker):
        """测试配置修改后未重启的检测"""
        import os
        from datetime import datetime, timezone, timedelta

        with test_app.app_context():
            success, result = ClientService.create_client({
                'name': 'needs-restart-test',
                'config_content': VALID_TOML_CONFIG,
                'frp_version': 'v0.61.1',
            })
            assert success
            client_id = result['id']

            # 未启动：不需要重启
            assert ProcessService.needs_restart(client_id) is False

            ok, msg = ProcessService.start(client_id)
            assert ok, f"启动应成功: {msg}"
            assert ProcessService.get_status(client_id) == 'running'

            config_path = ProcessService._config_path(client_id)
            assert os.path.exists(config_path)

            # 启动后修改配置 → 需要重启
            future = datetime.now(timezone.utc) + timedelta(minutes=5)
            os.utime(config_path, (future.timestamp(), future.timestamp()))
            assert ProcessService.needs_restart(client_id) is True

            # 把 mtime 改回启动前 → 不需要重启
            past = datetime.now(timezone.utc) - timedelta(minutes=5)
            os.utime(config_path, (past.timestamp(), past.timestamp()))
            assert ProcessService.needs_restart(client_id) is False

            # 停止后：不算需要重启
            ProcessService.stop(client_id)
            assert ProcessService.needs_restart(client_id) is False
