"""
数据库连接和初始化模块
"""
import sqlite3
from flask import g

from config import Config
from utils.logger import ColorLogger


def init_db() -> None:
    """初始化数据库，创建表和索引"""
    conn = sqlite3.connect(Config.DATABASE_URL)
    c = conn.cursor()

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 旧数据库迁移：添加缺失的字段
    for col, definition in [
        ('status', "TEXT DEFAULT 'stopped'"),
        ('server_port', 'INTEGER DEFAULT 7000'),
        ('token', 'TEXT'),
        ('user', 'TEXT'),
    ]:
        try:
            c.execute(f'SELECT {col} FROM clients LIMIT 1')
        except sqlite3.OperationalError:
            c.execute(f'ALTER TABLE clients ADD COLUMN {col} {definition}')
            ColorLogger.info(f'已添加 {col} 字段', 'Database')

    # 启用 WAL 模式
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=NORMAL')

    conn.commit()
    conn.close()
    ColorLogger.success('数据库初始化完成', 'Database')


def get_db():
    """获取数据库连接（请求上下文）"""
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE_URL, timeout=30)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA synchronous=NORMAL')
    return g.db


def close_db(exception=None) -> None:
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()
