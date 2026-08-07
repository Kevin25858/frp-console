"""
配置管理模块
从环境变量读取配置，设置管理员账号、密钥等

为什么用环境变量而不是写死在代码里：
    1. 安全：密码、密钥这类敏感信息不能写进代码仓库（会被 git 追踪）
    2. 灵活：不同环境（开发/测试/生产）用不同配置，不用改代码
    3. 容器化友好：Docker 部署时通过 docker-compose 的 environment 注入

为什么用一个 Config 类：
    把所有配置集中到一个类里，方便统一管理。
    类属性在模块导入时就计算，整个程序都能用 Config.XXX 访问。
"""
import os
import secrets

from utils.logger import ColorLogger


class Config:
    """应用配置类"""

    # 服务端口
    # 从环境变量读 PORT，没设置就用默认的 7600
    # int() 把读到的字符串转成整数
    PORT = int(os.environ.get('PORT', 7600))

    # Flask 会话密钥
    # 用途：给 session cookie 签名，防止被伪造
    # 没设置就随机生成，但这样每次重启都会变，用户需要重新登录
    # 生产环境一定要在 .env 里固定一个 SECRET_KEY
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # 配置导出 API 的认证令牌
    # 用途：frpc 客户端可以通过 API 拉取自己的配置（/api/configs/<id>/export）
    # 这样不用登录就能拿到配置，但要带正确的 API_TOKEN
    # 如果不设置，这个功能就不可用
    API_TOKEN = os.environ.get('API_TOKEN')

    # 目录配置
    # BASE_DIR 是项目根目录，用于定位 logs 和 data 目录
    # 优先用环境变量，没设置就自动判断：
    #   - /app 是 Docker 容器内的路径
    #   - /opt/frp-console 是裸机部署的路径
    #   - 都没有就用项目源码的上级目录（开发环境）
    BASE_DIR = os.environ.get('BASE_DIR')
    if not BASE_DIR:
        if os.path.exists('/app'):
            BASE_DIR = '/app'
        elif os.path.exists('/opt/frp-console'):
            BASE_DIR = '/opt/frp-console'
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 日志和数据目录
    # LOGS_DIR 存放运行日志文件
    # DATA_DIR 存放 SQLite 数据库文件
    # 默认放在 BASE_DIR 下面，也可以用环境变量单独指定
    LOGS_DIR = os.environ.get('LOGS_DIR', os.path.join(BASE_DIR, 'logs'))
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))

    # 数据库路径
    # SQLite 是文件型数据库，配置就是一个文件路径
    # .replace('sqlite:///', '') 是为了兼容 SQLAlchemy 风格的连接串
    # 用户可能在环境变量里写 'sqlite:///path/to/db'，去掉前缀就是纯路径
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(DATA_DIR, 'frpc.db')
    ).replace('sqlite:///', '')

    # Session 配置
    # 会话有效期 24 小时（86400 秒）
    # 用户登录后，cookie 会在 24 小时后过期
    PERMANENT_SESSION_LIFETIME = 86400  # 24 小时（单位秒）

    # 每次请求都刷新会话过期时间
    # 这样用户持续操作就不会被强制登出
    SESSION_REFRESH_EACH_REQUEST = True

    # 登录速率限制
    # 防止暴力破解密码：失败 N 次后锁定一段时间
    MAX_LOGIN_ATTEMPTS = 5       # 最多尝试 5 次
    LOGIN_LOCKOUT_TIME = 900     # 锁定 15 分钟（单位秒）

    # 管理员配置（在 init() 中从环境变量加载）
    # 这里先声明为 None，启动时 load_admin_config() 会填充实际值
    ADMIN_USER = None
    ADMIN_PASSWORD = None
    PASSWORD_SALT = None

    @classmethod
    def load_admin_config(cls):
        """
        从环境变量加载管理员账号和密码

        为什么密码要哈希存储：
            即使数据库或内存被泄露，攻击者也拿不到明文密码。
            哈希是单向的，无法从哈希值反推出原密码。
        """
        # 默认用户名是 admin，也可以用环境变量改
        admin_user = os.environ.get('ADMIN_USER', 'admin')
        env_password = os.environ.get('ADMIN_PASSWORD')

        if env_password:
            # 用环境变量的密码
            # 哈希后存到类属性（不存明文）
            from utils.password import hash_password
            password_salt, password_hash = hash_password(env_password)
            ColorLogger.info('使用环境变量配置的密码', 'Config')
        else:
            # 没设置密码，随机生成一个
            # 这是为了避免用户忘记配置导致系统无密码可登录
            # 生成的密码会打印到日志里，提醒用户保存
            admin_user = 'admin'
            random_password = secrets.token_urlsafe(16)
            from utils.password import hash_password
            password_salt, password_hash = hash_password(random_password)

            # 打印随机密码，提醒用户保存
            # 注意：这里只在没配置密码时打印，生产环境应该总是配置 ADMIN_PASSWORD
            ColorLogger.warning('=' * 60, 'Security')
            ColorLogger.warning('未配置管理员密码！已生成随机密码：', 'Security')
            ColorLogger.warning('用户名: ' + admin_user, 'Security')
            ColorLogger.warning('密码: ' + random_password, 'Security')
            ColorLogger.warning('请使用上述凭据登录，并在设置中修改密码', 'Security')
            ColorLogger.warning('=' * 60, 'Security')

        cls.ADMIN_USER = admin_user
        cls.ADMIN_PASSWORD = password_hash
        cls.PASSWORD_SALT = password_salt
        return admin_user, password_hash

    @classmethod
    def init(cls):
        """
        初始化配置（启动时调用一次）

        为什么单独抽一个 init 方法：
            1. 模块导入时不一定就要初始化（比如测试时可能想跳过）
            2. 把"加载管理员密码"和"检查环境变量"这些副作用集中起来
            3. 控制初始化顺序，避免循环依赖
        """
        cls.load_admin_config()

        # 检查必需的环境变量
        # 这些不是必须的，但缺失会有安全风险，所以给个警告
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

        # 创建日志和数据目录
        # exist_ok=True 表示目录已存在也不报错
        # 这是为了首次启动时自动创建目录，避免后续写文件失败
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)


# 启动时自动初始化
# 这样 import config 时就会触发初始化，不需要在 app.py 里手动调用
Config.init()
