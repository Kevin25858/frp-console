"""
用户表迁移脚本
将现有管理员配置迁移到 users 表
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from utils.logger import ColorLogger


def migrate_admin_to_users():
    """将现有管理员配置迁移到 users 表"""
    import os
    conn = sqlite3.connect(Config.DATABASE_URL)
    c = conn.cursor()

    try:
        # 检查是否已有用户数据
        c.execute('SELECT COUNT(*) FROM users')
        count = c.fetchone()[0]

        # 如果环境变量设置了 ADMIN_PASSWORD，强制更新密码
        env_password = os.environ.get('ADMIN_PASSWORD')
        if env_password and count > 0:
            from utils.password import hash_password
            password_salt, password_hash = hash_password(env_password)
            c.execute('''
                UPDATE users SET password_hash = ?, password_salt = ?
                WHERE username = ?
            ''', (password_hash, password_salt, Config.ADMIN_USER))
            conn.commit()
            ColorLogger.success(f'已使用环境变量更新管理员密码: {Config.ADMIN_USER}', 'Migration')
            conn.close()
            return

        if count > 0:
            ColorLogger.info('用户表已有数据，跳过迁移', 'Migration')
            conn.close()
            return

        # 从配置加载管理员信息
        admin_user = Config.ADMIN_USER
        admin_password = Config.ADMIN_PASSWORD
        password_salt = Config.PASSWORD_SALT

        if admin_user and admin_password and password_salt:
            # 插入管理员用户
            c.execute('''
                INSERT INTO users (username, password_hash, password_salt, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (admin_user, admin_password, password_salt, 'admin', 1))

            conn.commit()
            ColorLogger.success(f'成功迁移管理员用户: {admin_user}', 'Migration')
        else:
            ColorLogger.warning('未找到管理员配置，无法迁移', 'Migration')

    except Exception as e:
        ColorLogger.error(f'迁移失败: {e}', 'Migration')
        conn.rollback()
    finally:
        conn.close()


def add_user_id_to_audit_logs():
    """为审计日志表添加 user_id 字段"""
    conn = sqlite3.connect(Config.DATABASE_URL)
    c = conn.cursor()

    try:
        # 检查是否已有 user_id 字段
        c.execute('PRAGMA table_info(audit_logs)')
        columns = [row[1] for row in c.fetchall()]

        if 'user_id' not in columns:
            # 添加 user_id 字段
            c.execute('ALTER TABLE audit_logs ADD COLUMN user_id INTEGER')

            # 创建索引
            c.execute('CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)')

            conn.commit()
            ColorLogger.success('成功为审计日志表添加 user_id 字段', 'Migration')
        else:
            ColorLogger.info('审计日志表已有 user_id 字段，跳过', 'Migration')

    except Exception as e:
        ColorLogger.error(f'添加 user_id 字段失败: {e}', 'Migration')
        conn.rollback()
    finally:
        conn.close()


def run_migrations():
    """运行所有迁移"""
    ColorLogger.info('开始用户表迁移...', 'Migration')

    # 确保数据库已初始化
    from models.database import init_db
    init_db()

    # 运行迁移
    migrate_admin_to_users()
    add_user_id_to_audit_logs()

    ColorLogger.success('用户表迁移完成', 'Migration')


if __name__ == '__main__':
    run_migrations()
