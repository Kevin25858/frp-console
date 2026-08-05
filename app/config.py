"""
配置管理模块
"""
import os
import secrets

from utils.logger import ColorLogger


class Config:
    """应用配置类"""

    PORT = int(os.environ.get('PORT', 7600))
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    API_TOKEN = os.environ.get('API_TOKEN')

    # 目录配置
    BASE_DIR = os.environ.get('BASE_DIR')
    if not BASE_DIR:
        if os.path.exists('/app'):
            BASE_DIR = '/app'
        elif os.path.exists('/opt/frp-console'):
            BASE_DIR = '/opt/frp-console'
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    LOGS_DIR = os.environ.get('LOGS_DIR', os.path.join(BASE_DIR, 'logs'))
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))

    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{DATA_DIR}/frpc.db'
    ).replace('sqlite:///', '')

    # Session 配置
    PERMANENT_SESSION_LIFETIME = 86400  # 24小时
    SESSION_REFRESH_EACH_REQUEST = True

    # 登录速率限制
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_TIME = 900  # 15分钟

    # 管理员配置
    ADMIN_USER = None
    ADMIN_PASSWORD = None
    PASSWORD_SALT = None

    @classmethod
    def load_admin_config(cls) -> tuple:
        """从环境变量加载管理员配置"""
        admin_user = os.environ.get('ADMIN_USER', 'admin')
        env_password = os.environ.get('ADMIN_PASSWORD')

        if env_password:
            from utils.password import hash_password
            password_salt, password_hash = hash_password(env_password)
            ColorLogger.info('使用环境变量配置的密码', 'Config')
        else:
            # 生成随机密码
            admin_user = 'admin'
            random_password = secrets.token_urlsafe(16)
            from utils.password import hash_password
            password_salt, password_hash = hash_password(random_password)

            ColorLogger.warning('=' * 60, 'Security')
            ColorLogger.warning('未配置管理员密码！已生成随机密码：', 'Security')
            ColorLogger.warning(f'用户名: {admin_user}', 'Security')
            ColorLogger.warning(f'密码: {random_password}', 'Security')
            ColorLogger.warning('请使用上述凭据登录，并在设置中修改密码', 'Security')
            ColorLogger.warning('=' * 60, 'Security')

        cls.ADMIN_USER = admin_user
        cls.ADMIN_PASSWORD = password_hash
        cls.PASSWORD_SALT = password_salt
        return admin_user, password_hash

    @classmethod
    def init(cls):
        """初始化配置"""
        cls.load_admin_config()

        if not os.environ.get('SECRET_KEY'):
            ColorLogger.warning(
                '未设置 SECRET_KEY 环境变量，已生成随机密钥。重启后需重新登录！',
                'Security'
            )

        if not cls.API_TOKEN:
            ColorLogger.warning(
                '未设置 API_TOKEN 环境变量，frpc 将无法通过 API 拉取配置',
                'Security'
            )

        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)


Config.init()
