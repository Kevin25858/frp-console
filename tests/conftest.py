"""
Pytest 配置和共享 fixture
"""
import pytest
import sys
import os

# 添加项目根目录和 app 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))


@pytest.fixture(autouse=True)
def clear_login_attempts():
    """每个测试前清除速率限制状态"""
    from utils.helpers import login_attempts
    login_attempts.clear()
    yield
    login_attempts.clear()


@pytest.fixture
def test_config():
    """测试配置 fixture"""
    from config import Config
    return Config


@pytest.fixture
def test_database(tmp_path):
    """测试数据库 fixture"""
    import sqlite3
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))

    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            config_content TEXT NOT NULL,
            local_port INTEGER,
            remote_port INTEGER,
            server_addr TEXT,
            server_port INTEGER DEFAULT 7000,
            token TEXT,
            user TEXT,
            status TEXT DEFAULT 'stopped',
            enabled BOOLEAN DEFAULT 1,
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
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    from app.app import create_app
    from config import Config

    import tempfile
    original_user = Config.ADMIN_USER
    original_salt = Config.PASSWORD_SALT
    original_password = Config.ADMIN_PASSWORD
    original_db_url = Config.DATABASE_URL

    # 使用临时数据库
    tmp_dir = tempfile.mkdtemp()
    Config.DATABASE_URL = os.path.join(tmp_dir, 'test.db')

    try:
        app = create_app(testing=True)
        app.config['TESTING'] = True

        Config.ADMIN_USER = 'test_admin'
        Config.PASSWORD_SALT = 'test_salt'
        Config.ADMIN_PASSWORD = 'test_hashed_password'

        # 初始化测试数据库
        from models.database import init_db
        init_db()

        yield app
    finally:
        Config.ADMIN_USER = original_user
        Config.PASSWORD_SALT = original_salt
        Config.ADMIN_PASSWORD = original_password
        Config.DATABASE_URL = original_db_url


@pytest.fixture
def test_client(test_app):
    """测试客户端 fixture"""
    return test_app.test_client()


@pytest.fixture
def test_auth_headers(test_client):
    """测试认证 headers fixture"""
    test_client.post('/login', data={
        'username': 'test_admin',
        'password': 'test_password'
    })
    return {}
