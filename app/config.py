"""
配置管理模块
集中管理应用的所有配置项，支持环境变量和配置文件
"""
import os
import secrets
from typing import Dict, Any

from utils.logger import ColorLogger


class Config:
    """应用配置类"""

    # 基础配置
    PORT = int(os.environ.get('PORT', 7600))
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # 数据库配置
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'sqlite:////opt/frp-console/data/frpc.db'
    ).replace('sqlite:///', '')

    # 目录配置
    # 根据环境自动判断基础目录（容器内用 /app，宿主机用 /opt/frp-console）
    if os.path.exists('/app/frpc/frpc'):
        BASE_DIR = '/app'
    else:
        BASE_DIR = '/opt/frp-console'
    CONFIGS_DIR = os.path.join(BASE_DIR, 'clients')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    FRPC_BINARY = os.path.join(BASE_DIR, 'frpc', 'frpc')
    CONFIG_FILE = os.path.join(BASE_DIR, 'frp-console.conf')

    # Session 配置
    PERMANENT_SESSION_LIFETIME = 86400  # 24小时
    SESSION_REFRESH_EACH_REQUEST = True

    # 登录速率限制配置
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_TIME = 900  # 15分钟

    # 重启管理配置
    MAX_RESTARTS_PER_WINDOW = 3
    RESTART_WINDOW = 300  # 5分钟
    RESTART_COOLDOWN = 10  # 重启间隔10秒

    # 健康检查配置
    HEALTH_CHECK_INTERVAL = 10  # 10秒

    # 管理员配置
    ADMIN_USER = None
    ADMIN_PASSWORD = None
    PASSWORD_SALT = None

    # SMTP 配置（无默认值，必须通过环境变量配置）
    SMTP_CONFIG: Dict[str, Any] = {
        'host': os.environ.get('SMTP_HOST'),
        'port': int(os.environ.get('SMTP_PORT', 587)) if os.environ.get('SMTP_PORT') else None,
        'user': os.environ.get('SMTP_USER'),
        'password': os.environ.get('SMTP_PASSWORD'),
        'to': os.environ.get('ALERT_TO', '').split(',') if os.environ.get('ALERT_TO') else []
    }

    @classmethod
    def load_admin_config(cls) -> tuple:
        """从配置文件或环境变量加载管理员配置"""
        password_salt = None
        password_hash = None

        # 优先从环境变量读取密码（ADMIN_PASSWORD 单独设置即可）
        admin_user = os.environ.get('ADMIN_USER', 'admin')  # 默认用户名 admin
        env_password = os.environ.get('ADMIN_PASSWORD')

        if env_password:
            # 环境变量中的密码需要哈希
            from utils.password import hash_password
            password_salt, password_hash = hash_password(env_password)
            ColorLogger.info('使用环境变量配置的密码', 'Config')
        elif os.path.exists(cls.CONFIG_FILE):
            # 如果环境变量未设置，尝试从配置文件读取
            try:
                config_user = None
                config_password = None
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                if key == 'ADMIN_USER':
                                    config_user = value
                                elif key == 'ADMIN_PASSWORD':
                                    # 检查是否是哈希格式（salt:hash）
                                    if ':' in value:
                                        password_salt, password_hash = value.split(':', 1)
                                        config_password = value
                                    else:
                                        # 旧式明文密码，转换为哈希
                                        from utils.password import hash_password
                                        password_salt, password_hash = hash_password(value)
                                        config_password = f"{password_salt}:{password_hash}"
                                        # 更新配置文件
                                        cls._update_password_in_config(password_salt, password_hash)
                        except ValueError as e:
                            ColorLogger.warning(f'配置文件第 {line_num} 行格式错误: {e}', 'Config')
                            continue
                
                if config_user and config_password:
                    admin_user = config_user
                    ColorLogger.info('使用配置文件中的管理员账户', 'Config')
                else:
                    admin_user = None
            except Exception as e:
                ColorLogger.warning(f'无法读取配置文件: {e}', 'Config')
                admin_user = None
        else:
            admin_user = None

        # 如果没有配置管理员账户，生成随机密码
        if not admin_user or not password_hash:
            import secrets
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
    def _update_password_in_config(cls, salt: str, password_hash: str):
        """更新配置文件中的密码为哈希格式"""
        try:
            lines = []
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('ADMIN_PASSWORD='):
                        f.write(f'ADMIN_PASSWORD={salt}:{password_hash}\n')
                    else:
                        f.write(line)
        except Exception as e:
            ColorLogger.error(f'无法更新配置文件密码: {e}', 'Config')

    @classmethod
    def init(cls):
        """初始化配置"""
        # 加载管理员配置
        cls.load_admin_config()

        # 检查默认密码
        if cls.ADMIN_PASSWORD == 'admin123':
            ColorLogger.warning('使用默认密码，请及时修改！', 'Security')

        # 检查 SECRET_KEY
        if not os.environ.get('SECRET_KEY'):
            ColorLogger.warning(
                '⚠️ 未设置 SECRET_KEY 环境变量，已生成随机密钥。重启后需重新登录！',
                'Security'
            )

        # 检查 SMTP 密码
        if not cls.SMTP_CONFIG['password']:
            ColorLogger.warning('未设置 SMTP_PASSWORD，告警功能将无法使用', 'SMTP')

        # 确保必要的目录存在
        os.makedirs(cls.CONFIGS_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.LOGS_DIR, 'frpc'), exist_ok=True)


# 初始化配置
Config.init()
