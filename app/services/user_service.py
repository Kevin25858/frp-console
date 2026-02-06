"""
用户服务模块
提供用户管理相关的业务逻辑
"""
from typing import Optional, List, Dict, Any
from models.database import get_db_connection
from utils.password import hash_password, verify_password
from utils.logger import ColorLogger


class UserService:
    """用户服务类"""

    ROLES = ['admin', 'operator', 'viewer']

    @staticmethod
    def create_user(username: str, password: str, role: str = 'viewer') -> Dict[str, Any]:
        """
        创建新用户

        Args:
            username: 用户名
            password: 密码
            role: 角色 (admin/operator/viewer)

        Returns:
            Dict: 包含成功状态和用户信息或错误信息
        """
        if role not in UserService.ROLES:
            return {'success': False, 'error': f'无效的角色: {role}'}

        if len(username) < 3:
            return {'success': False, 'error': '用户名至少需要3个字符'}

        if len(password) < 8:
            return {'success': False, 'error': '密码至少需要8个字符'}

        conn = get_db_connection()
        c = conn.cursor()

        try:
            # 检查用户名是否已存在
            c.execute('SELECT id FROM users WHERE username = ?', (username,))
            if c.fetchone():
                return {'success': False, 'error': '用户名已存在'}

            # 哈希密码
            password_salt, password_hash = hash_password(password)

            # 插入用户
            c.execute('''
                INSERT INTO users (username, password_hash, password_salt, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, password_salt, role, 1))

            user_id = c.lastrowid
            conn.commit()

            ColorLogger.info(f'创建用户成功: {username} (ID: {user_id})', 'UserService')

            return {
                'success': True,
                'user': {
                    'id': user_id,
                    'username': username,
                    'role': role,
                    'is_active': True
                }
            }

        except Exception as e:
            conn.rollback()
            ColorLogger.error(f'创建用户失败: {e}', 'UserService')
            return {'success': False, 'error': f'创建用户失败: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def get_users() -> List[Dict[str, Any]]:
        """
        获取所有用户列表

        Returns:
            List[Dict]: 用户列表
        """
        conn = get_db_connection()
        c = conn.cursor()

        try:
            c.execute('''
                SELECT id, username, role, is_active, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
            ''')

            users = []
            for row in c.fetchall():
                users.append({
                    'id': row[0],
                    'username': row[1],
                    'role': row[2],
                    'is_active': bool(row[3]),
                    'created_at': row[4],
                    'updated_at': row[5]
                })

            return users

        except Exception as e:
            ColorLogger.error(f'获取用户列表失败: {e}', 'UserService')
            return []
        finally:
            conn.close()

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Dict 或 None: 用户信息
        """
        conn = get_db_connection()
        c = conn.cursor()

        try:
            c.execute('''
                SELECT id, username, role, is_active, created_at, updated_at
                FROM users
                WHERE id = ?
            ''', (user_id,))

            row = c.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'is_active': bool(row[3]),
                'created_at': row[4],
                'updated_at': row[5]
            }

        except Exception as e:
            ColorLogger.error(f'获取用户信息失败: {e}', 'UserService')
            return None
        finally:
            conn.close()

    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """
        根据用户名获取用户信息（包含密码信息，用于登录验证）

        Args:
            username: 用户名

        Returns:
            Dict 或 None: 用户信息
        """
        conn = get_db_connection()
        c = conn.cursor()

        try:
            c.execute('''
                SELECT id, username, password_hash, password_salt, role, is_active
                FROM users
                WHERE username = ?
            ''', (username,))

            row = c.fetchone()
            if not row:
                return None

            return {
                'id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'password_salt': row[3],
                'role': row[4],
                'is_active': bool(row[5])
            }

        except Exception as e:
            ColorLogger.error(f'获取用户信息失败: {e}', 'UserService')
            return None
        finally:
            conn.close()

    @staticmethod
    def update_user(user_id: int, role: Optional[str] = None,
                    is_active: Optional[bool] = None) -> Dict[str, Any]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            role: 新角色
            is_active: 是否激活

        Returns:
            Dict: 包含成功状态和错误信息
        """
        conn = get_db_connection()
        c = conn.cursor()

        try:
            # 检查用户是否存在
            c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
            if not c.fetchone():
                return {'success': False, 'error': '用户不存在'}

            updates = []
            params = []

            if role is not None:
                if role not in UserService.ROLES:
                    return {'success': False, 'error': f'无效的角色: {role}'}
                updates.append('role = ?')
                params.append(role)

            if is_active is not None:
                updates.append('is_active = ?')
                params.append(1 if is_active else 0)

            if not updates:
                return {'success': False, 'error': '没有要更新的字段'}

            params.append(user_id)

            c.execute(f'''
                UPDATE users
                SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', params)

            conn.commit()

            ColorLogger.info(f'更新用户成功: ID {user_id}', 'UserService')
            return {'success': True}

        except Exception as e:
            conn.rollback()
            ColorLogger.error(f'更新用户失败: {e}', 'UserService')
            return {'success': False, 'error': f'更新用户失败: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def delete_user(user_id: int) -> Dict[str, Any]:
        """
        删除用户

        Args:
            user_id: 用户ID

        Returns:
            Dict: 包含成功状态和错误信息
        """
        conn = get_db_connection()
        c = conn.cursor()

        try:
            # 检查用户是否存在
            c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            row = c.fetchone()
            if not row:
                return {'success': False, 'error': '用户不存在'}

            # 不能删除最后一个管理员
            if row[0] == 'admin':
                c.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('admin',))
                admin_count = c.fetchone()[0]
                if admin_count <= 1:
                    return {'success': False, 'error': '不能删除最后一个管理员'}

            c.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()

            ColorLogger.info(f'删除用户成功: ID {user_id}', 'UserService')
            return {'success': True}

        except Exception as e:
            conn.rollback()
            ColorLogger.error(f'删除用户失败: {e}', 'UserService')
            return {'success': False, 'error': f'删除用户失败: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def reset_password(user_id: int, new_password: str) -> Dict[str, Any]:
        """
        重置用户密码

        Args:
            user_id: 用户ID
            new_password: 新密码

        Returns:
            Dict: 包含成功状态和错误信息
        """
        if len(new_password) < 8:
            return {'success': False, 'error': '密码至少需要8个字符'}

        conn = get_db_connection()
        c = conn.cursor()

        try:
            # 检查用户是否存在
            c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
            if not c.fetchone():
                return {'success': False, 'error': '用户不存在'}

            # 哈希新密码
            password_salt, password_hash = hash_password(new_password)

            c.execute('''
                UPDATE users
                SET password_hash = ?, password_salt = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (password_hash, password_salt, user_id))

            conn.commit()

            ColorLogger.info(f'重置密码成功: ID {user_id}', 'UserService')
            return {'success': True}

        except Exception as e:
            conn.rollback()
            ColorLogger.error(f'重置密码失败: {e}', 'UserService')
            return {'success': False, 'error': f'重置密码失败: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def verify_user_password(username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        验证用户密码

        Args:
            username: 用户名
            password: 密码

        Returns:
            Dict 或 None: 验证成功返回用户信息，失败返回None
        """
        user = UserService.get_user_by_username(username)
        if not user:
            return None

        if not user['is_active']:
            return None

        if verify_password(password, user['password_salt'], user['password_hash']):
            return {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'is_active': user['is_active']
            }

        return None

    @staticmethod
    def count_users() -> int:
        """
        获取用户总数

        Returns:
            int: 用户数量
        """
        conn = get_db_connection()
        c = conn.cursor()

        try:
            c.execute('SELECT COUNT(*) FROM users')
            return c.fetchone()[0]
        except Exception as e:
            ColorLogger.error(f'获取用户数量失败: {e}', 'UserService')
            return 0
        finally:
            conn.close()
