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

    # 客户端表
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            config_path TEXT NOT NULL,
            local_port INTEGER,
            remote_port INTEGER,
            server_addr TEXT,
            status TEXT DEFAULT 'stopped',
            enabled BOOLEAN DEFAULT 1,
            always_on BOOLEAN DEFAULT 0,
            traffic_in_cache BIGINT DEFAULT 0,
            traffic_out_cache BIGINT DEFAULT 0,
            connections_active_cache INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 检查并添加 always_on 字段（兼容旧数据库）
    try:
        c.execute('SELECT always_on FROM clients LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE clients ADD COLUMN always_on BOOLEAN DEFAULT 0')
        ColorLogger.info('已添加 always_on 字段到 clients 表', 'Database')

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

    # 流量统计表（监控功能已移除）
    c.execute('''
        CREATE TABLE IF NOT EXISTS traffic_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            traffic_in BIGINT DEFAULT 0,
            traffic_out BIGINT DEFAULT 0,
            connections_active INTEGER DEFAULT 0,
            connections_total INTEGER DEFAULT 0,
            rate_in INTEGER DEFAULT 0,
            rate_out INTEGER DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')

    # 创建索引（监控功能已移除）
    c.execute('CREATE INDEX IF NOT EXISTS idx_stats_client_time ON traffic_stats(client_id, timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_stats_time ON traffic_stats(timestamp)')

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