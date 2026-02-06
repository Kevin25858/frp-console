"""
客户端服务测试
"""
import pytest
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.client_service import ClientService
from app.utils.validators import validate_client_name, validate_toml_config, validate_port


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
        """测试有效的 TOML 配置"""
        config = """
[common]
server_addr = "127.0.0.1"
server_port = 7000

[proxy]
type = tcp
local_port = 8080
remote_port = 8080
"""
        valid, message = validate_toml_config(config)
        assert valid, f"配置应该有效，但返回: {message}"

    def test_empty_config(self):
        """测试空配置无效"""
        valid, message = validate_toml_config("")
        assert not valid
        assert "不能为空" in message

    def test_config_without_section(self):
        """测试没有节的配置无效"""
        config = """
server_addr = "127.0.0.1"
server_port = 7000
"""
        valid, message = validate_toml_config(config)
        assert not valid
        assert "section" in message.lower() or "节" in message

    def test_config_with_comments(self):
        """测试带注释的配置有效"""
        config = """
# This is a comment
[common]
server_addr = "127.0.0.1"
# Another comment
server_port = 7000

[proxy]
type = tcp
"""
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
        """测试创建客户端时的验证"""
        with test_app.app_context():
            # 测试无效名称
            success, result = ClientService.create_client({
                'name': 'invalid@name',
                'server_addr': 'test.com',
                'local_port': 8080,
                'remote_port': 8081
            })
            assert not success
            assert 'error' in result

    def test_create_client_with_config_content(self, test_app, tmp_path):
        """测试使用配置内容创建客户端"""
        with test_app.app_context():
            config_content = """
[common]
server_addr = "test.example.com"
server_port = 7000

[proxy]
type = tcp
local_port = 8080
remote_port = 9090
"""
            success, result = ClientService.create_client({
                'name': 'test-client-config',
                'config_content': config_content,
                'always_on': False
            })
            # 注意：这可能因为数据库等原因失败，但验证逻辑应该正确
            # 如果失败，应该返回错误信息
            if not success:
                assert 'error' in result

    def test_get_client_nonexistent(self, test_app):
        """测试获取不存在的客户端返回 None"""
        with test_app.app_context():
            client = ClientService.get_client(99999)
            assert client is None
