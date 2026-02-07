"""
数据库连接和初始化模块
"""
import sqlite3
from flask import g

from config import Config
from utils.logger import ColorLogger


def init_db() -> None:
    """初始化数据库，创建所有表和索引"""
    conn = sqlite3.connect(Config.DATABASE_URL)
    c = conn.cursor()

    # 客户端表 - 配置内容直接存储在数据库中
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            config_content TEXT NOT NULL,
            local_port INTEGER,
            remote_port INTEGER,
            server_addr TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 检查是否需要迁移旧数据（从文件存储迁移到数据库存储）
    try:
        c.execute('SELECT config_path FROM clients LIMIT 1')
        # 如果存在 config_path 字段，说明是旧数据库，需要迁移
        ColorLogger.info('检测到旧数据库结构，需要进行迁移', 'Database')
        # 这里可以添加迁移逻辑，但简化起见，我们直接创建新表
    except sqlite3.OperationalError:
        # 不存在 config_path 字段，说明是新数据库或已迁移
        pass

    # 日志表
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            level TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')

    # 告警表
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            alert_type TEXT,
            message TEXT,
            sent_to TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')

    # 审计日志表
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            level TEXT DEFAULT 'INFO',
            user TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 审计日志索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)')

    # 用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 用户表索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')

    # 启用 WAL 模式以提高并发性能
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=NORMAL')

    conn.commit()
    conn.close()
    ColorLogger.success('数据库初始化完成', 'Database')


def get_db():
    """
    获取数据库连接（用于请求上下文）

    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE_URL, timeout=30)
        g.db.row_factory = sqlite3.Row
        # 启用 WAL 模式以提高并发性能
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA synchronous=NORMAL')
    return g.db


def get_db_connection():
    """
    获取独立的数据库连接（用于后台线程，不依赖 Flask 上下文）

    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    conn = sqlite3.connect(Config.DATABASE_URL, timeout=30)
    conn.row_factory = sqlite3.Row
    # 启用 WAL 模式以提高并发性能
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn


def close_db(exception=None) -> None:
    """
    关闭数据库连接

    Args:
        exception: 异常对象（由 Flask 传入）
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()
