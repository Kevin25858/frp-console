"""
Pytest 配置和共享 fixture
"""
import pytest
import sys
import os

# 添加项目根目录和 app 目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# 测试专用账户
TEST_ADMIN_USER = 'test_admin'
TEST_ADMIN_PASSWORD = 'test_password_123'


@pytest.fixture(autouse=True)
def clear_login_attempts():
    """每个测试前清除速率限制状态"""
    from utils.helpers import login_attempts
    login_attempts.clear()
    yield
    login_attempts.clear()


@pytest.fixture(autouse=True)
def mock_docker(monkeypatch, tmp_path):
    """mock Docker SDK，避免测试触碰真实 Docker 守护进程。

    将 ProcessService._docker 替换为伪对象，提供 containers/images 的最小接口。
    同时将配置目录重定向到临时目录，避免写入 /opt/frpc。
    """
    import services.process_service as ps_module
    from services.process_service import ProcessService

    # 重定向配置目录到临时目录
    test_configs_dir = str(tmp_path / "frp-client")
    monkeypatch.setattr(ps_module, 'CONFIGS_DIR', test_configs_dir)

    class FakeContainer:
        def __init__(self, name, status='stopped', health=None):
            self.name = name
            self.attrs = {
                'State': {
                    'Status': status,
                    'Health': {'Status': health} if health else {},
                }
            }
            self.logs_data = b''
            self._stopped = False
            self._removed = False

        def reload(self):
            pass

        def stop(self, timeout=None):
            self._stopped = True
            self.attrs['State']['Status'] = 'exited'

        def remove(self):
            self._removed = True

        def logs(self, tail=1000, timestamps=False):
            return self.logs_data

    class FakeContainerCollection:
        def __init__(self):
            self._store = {}
            self.run_calls = []

        def get(self, name):
            if name in self._store:
                return self._store[name]
            from docker.errors import NotFound
            raise NotFound(name)

        def run(self, image, **kwargs):
            name = kwargs.get('name', 'unknown')
            self.run_calls.append({'image': image, 'name': name, **kwargs})
            container = FakeContainer(name, status='running', health='healthy')
            self._store[name] = container
            return container

    class FakeImageCollection:
        def __init__(self):
            self.pull_calls = []

        def pull(self, image):
            self.pull_calls.append(image)

    class FakeDockerClient:
        def __init__(self):
            self.containers = FakeContainerCollection()
            self.images = FakeImageCollection()

    fake_client = FakeDockerClient()
    # 注入到类属性，使 _docker() 直接返回伪对象
    monkeypatch.setattr(ProcessService, '_client', fake_client)
    yield fake_client


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
            frp_version TEXT DEFAULT 'v0.61.1',
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    yield conn

    conn.close()


@pytest.fixture
def test_app():
    """测试 Flask 应用 fixture - 使用真实密码 hash 以便登录"""
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app'))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    from app.app import create_app
    from config import Config
    from utils.password import hash_password

    import tempfile
    original_user = Config.ADMIN_USER
    original_salt = Config.PASSWORD_SALT
    original_password = Config.ADMIN_PASSWORD
    original_db_url = Config.DATABASE_URL

    # 使用临时数据库
    tmp_dir = tempfile.mkdtemp()
    Config.DATABASE_URL = os.path.join(tmp_dir, 'test.db')

    # 生成真实密码 hash，使 test_auth_headers 可登录
    test_salt, test_hash = hash_password(TEST_ADMIN_PASSWORD)
    Config.ADMIN_USER = TEST_ADMIN_USER
    Config.PASSWORD_SALT = test_salt
    Config.ADMIN_PASSWORD = test_hash

    try:
        app = create_app(testing=True)
        app.config['TESTING'] = True

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
    """测试认证 headers fixture - 登录后返回空 dict（cookie 自动携带）"""
    test_client.post('/login', data={
        'username': TEST_ADMIN_USER,
        'password': TEST_ADMIN_PASSWORD
    })
    return {}
