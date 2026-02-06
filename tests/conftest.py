"""
Pytest 配置和共享 fixture
"""
import pytest
import sys
import os

# 添加项目根目录和 app 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))


@pytest.fixture
def test_config():
    """测试配置 fixture"""
    from app.config import Config
    return Config


@pytest.fixture
def test_database(tmp_path):
    """测试数据库 fixture"""
    import sqlite3
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # 创建测试表
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            config_path TEXT NOT NULL,
            local_port INTEGER,
            remote_port INTEGER,
            server_addr TEXT,
            status TEXT DEFAULT 'stopped',
            enabled BOOLEAN DEFAULT 1,
            always_on BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    yield conn
    
    conn.close()


@pytest.fixture
def test_app():
    """测试 Flask 应用 fixture"""
    from app.app import create_app
    app = create_app(testing=True)
    app.config['TESTING'] = True
    
    # 设置测试环境专用管理员账户
    from app.config import Config
    Config.ADMIN_USER = 'test_admin'
    Config.PASSWORD_SALT = 'test_salt'
    Config.ADMIN_PASSWORD = 'test_hashed_password'
    
    yield app


@pytest.fixture
def test_client(test_app):
    """测试客户端 fixture"""
    return test_app.test_client()


@pytest.fixture
def test_auth_headers(test_client):
    """测试认证 headers fixture"""
    # 使用测试环境专用账户登录
    test_client.post('/login', data={
        'username': 'test_admin',
        'password': 'test_password'
    })
    return {}
