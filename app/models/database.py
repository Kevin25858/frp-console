"""
数据库连接和初始化模块
使用 SQLite 数据库，只有一张 clients 表

为什么用 SQLite 而不是 MySQL/PostgreSQL：
    1. 零配置：不需要单独安装数据库服务，Python 自带 sqlite3 模块
    2. 文件型：整个数据库就是一个文件（frpc.db），备份/迁移很方便
    3. 性能够用：本项目数据量小（几十个客户端配置），SQLite 完全够用
    4. 并发安全：通过 WAL 模式可以支持多读单写，满足 Web 应用需求

什么是 WAL 模式：
    WAL = Write-Ahead Logging（预写式日志）
    普通模式下，写操作会锁住整个数据库，其他读操作要等待。
    WAL 模式下，写操作先写到日志文件，不阻塞读操作。
    适合"读多写少"的 Web 应用场景。
"""
import sqlite3
from flask import g

from config import Config
from utils.logger import ColorLogger


# 需要检查的字段列表（用于旧数据库迁移）
# 格式：(字段名, 字段类型定义)
# 用途：项目升级时，老用户的数据库可能没有新字段，
#       这里检查并自动补上，避免用户手动改数据库
NEED_CHECK_COLUMNS = [
    ('status', "TEXT DEFAULT 'stopped'"),
    ('server_port', 'INTEGER DEFAULT 7000'),
    ('token', 'TEXT'),
    ('user', 'TEXT'),
    ('frp_version', "TEXT DEFAULT 'v0.61.1'"),
    ('image', 'TEXT'),
    ('config_dirty', 'INTEGER DEFAULT 0'),
]


def init_db():
    """初始化数据库，创建表和索引"""
    # 连接数据库（文件不存在会自动创建）
    conn = sqlite3.connect(Config.DATABASE_URL)
    c = conn.cursor()

    # 创建 clients 表（如果不存在）
    # IF NOT EXISTS：表已存在时不报错，避免重复创建
    # 字段说明：
    #   id            主键，自增（每条记录自动 +1）
    #   name          客户端名称（用户起的，方便识别）
    #   config_content frpc 的 TOML 配置内容（核心数据）
    #   local_port    本地端口（展示用，从配置里解析出来）
    #   remote_port   远程端口（展示用，从配置里解析出来）
    #   server_addr   服务器地址（展示用）
    #   server_port   服务器端口（默认 7000，frps 的监听端口）
    #   token         FRP 鉴权 token
    #   user          FRP 用户名
    #   status        容器状态（stopped/running/error，展示用，每次查询实时更新）
    #   enabled       是否启用（0/1，批量操作用）
    #   frp_version   frp 版本号（决定用哪个镜像）
    #   image         自定义镜像名（可选，覆盖默认的 fatedier/frpc:version）
    #   created_at    创建时间
    #   updated_at    更新时间
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
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

    # 旧数据库迁移：检查并添加缺失的字段
    # 原理：尝试 SELECT 这个字段，如果不存在会抛 OperationalError
    #       捕获异常后用 ALTER TABLE 添加字段
    # 这是 SQLite 做轻量级迁移的常见手法
    for col_name, col_def in NEED_CHECK_COLUMNS:
        try:
            # 尝试查询这个字段，如果不存在会报错
            c.execute('SELECT ' + col_name + ' FROM clients LIMIT 1')
        except sqlite3.OperationalError:
            # 字段不存在，添加它
            c.execute('ALTER TABLE clients ADD COLUMN ' + col_name + ' ' + col_def)
            ColorLogger.info('已添加 ' + col_name + ' 字段', 'Database')

    # 启用 WAL 模式（提高并发性能）
    # 见模块开头对 WAL 的解释
    c.execute('PRAGMA journal_mode=WAL')
    # synchronous=NORMAL：稍微降低持久性保证，换取更高性能
    # 完全模式（FULL）每次写都 fsync，太慢；NORMAL 在崩溃时可能丢最后一笔写操作
    c.execute('PRAGMA synchronous=NORMAL')

    conn.commit()
    conn.close()
    ColorLogger.success('数据库初始化完成', 'Database')


def get_db():
    """
    获取数据库连接（在请求上下文中使用）
    同一个请求中多次调用会返回同一个连接

    为什么用 flask.g：
        flask.g 是请求级别的全局变量，同一个请求里共享。
        这样一个请求里多次操作数据库只开一个连接，请求结束自动关闭。
        避免了"每次操作都开新连接"的性能开销。
    """
    if 'db' not in g:
        # timeout=30：等锁最多等 30 秒
        # 如果别的请求正在写，SQLite 会锁库，这里设置等待避免立即报错
        g.db = sqlite3.connect(Config.DATABASE_URL, timeout=30)

        # row_factory = sqlite3.Row：让查询结果可以用字段名访问
        # 不设置的话，row[0]、row[1] 这样按下标访问，可读性差
        # 设置后可以 row['name']、row['id'] 这样按字段名访问
        g.db.row_factory = sqlite3.Row

        # 每个连接也启用 WAL（和 init_db 保持一致）
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA synchronous=NORMAL')
    return g.db


def close_db(exception=None):
    """
    关闭数据库连接（请求结束时自动调用）

    为什么参数是 exception：
        Flask 的 teardown_appcontext 回调会传入请求处理中发生的异常
        如果没异常传 None。我们可以根据是否有异常决定是否回滚，
        这里简单处理，统一关闭连接。
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()
