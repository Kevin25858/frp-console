"""
认证服务模块
单用户认证、CSRF 保护

为什么是单用户模式：
    本项目是"FRP 客户端管理控制台"，通常部署在个人服务器上，
    只有一个管理员使用。多用户系统会带来复杂的权限管理，
    对这个场景来说过度设计。

什么是 CSRF（跨站请求伪造）：
    攻击者诱导用户在已登录状态下，访问恶意网站，
    恶意网站向本站发送请求（浏览器会自动带上 cookie），
    从而冒充用户执行操作。
    防御方法：每次写操作要求带一个随机 token，攻击者拿不到这个 token。

为什么用 session 而不是 JWT：
    1. session 是有状态的（服务端保存登录态），可以主动让用户下线
    2. JWT 是无状态的，签发后无法撤销，到期前一直有效
    3. 单机部署用 session 更简单，不需要额外的存储
"""
import secrets
import hmac
from flask import session, request

from config import Config
from utils.logger import ColorLogger
from utils.helpers import check_login_rate_limit, record_login_attempt
from utils.validators import validate_password


class AuthService:
    """认证服务类 - 单用户模式"""

    # 所有方法都是 @staticmethod，因为单用户模式下不需要实例化
    # 直接用类名调用更简洁：AuthService.login(...) 而不是 AuthService().login(...)

    @staticmethod
    def get_csrf_token():
        """
        获取 CSRF token（不存在则生成一个新的）

        为什么存在 session 里：
            token 要服务端能验证，所以必须存一份。
            session 是按用户隔离的，每个用户有自己的 token。
        """
        if 'csrf_token' not in session:
            # token_urlsafe 生成 URL 安全的随机字符串
            # 32 字节足够长，暴力猜解不可能
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']

    @staticmethod
    def verify_csrf_token(token):
        """
        验证 CSRF token 是否正确

        为什么用 hmac.compare_digest 而不是 ==：
            == 比较会在第一个不同的字符就返回，攻击者可以通过
            测量响应时间逐字符猜解 token（时序攻击）。
            compare_digest 是恒定时间比较，无论哪里不同耗时都一样。
        """
        stored_token = session.get('csrf_token')
        if not stored_token or not token:
            return False
        return hmac.compare_digest(stored_token, token)

    @staticmethod
    def login(username, password):
        """用户登录，返回 (是否成功, 消息)"""
        # 获取客户端 IP（用于速率限制）
        client_ip = request.remote_addr

        # 先检查是否被锁定
        # 即使密码对，锁定期内也不让登，防止暴力破解
        allowed, message = check_login_rate_limit(
            client_ip, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME
        )
        if not allowed:
            return False, message

        if not username or not password:
            return False, '用户名或密码不能为空'

        # 验证用户名
        # 注意：用户名错误也返回"用户名或密码错误"
        # 不告诉具体是哪个错了，防止攻击者枚举用户名
        if username != Config.ADMIN_USER:
            record_login_attempt(client_ip, False, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME)
            ColorLogger.warning('登录失败: 用户名错误 (IP: ' + str(client_ip) + ')', 'Auth')
            return False, '用户名或密码错误'

        # 验证密码
        # 用 verify_password 比较，而不是直接 == 比较明文
        # 因为存储的是哈希值，需要用相同的盐值重新哈希再比较
        from utils.password import verify_password
        if not verify_password(password, Config.PASSWORD_SALT, Config.ADMIN_PASSWORD):
            record_login_attempt(client_ip, False, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME)
            ColorLogger.warning('登录失败: 密码错误 (IP: ' + str(client_ip) + ')', 'Auth')
            return False, '用户名或密码错误'

        # 登录成功，写入 session
        # session['logged_in'] = True 是登录态的标记
        # 后续请求只要 session 里有这个字段，就算已登录
        session['logged_in'] = True
        session['username'] = username
        # session.permanent = True 让会话按 PERMANENT_SESSION_LIFETIME 过期
        # 否则会在关闭浏览器时立即过期
        session.permanent = True
        record_login_attempt(client_ip, True, Config.MAX_LOGIN_ATTEMPTS, Config.LOGIN_LOCKOUT_TIME)
        ColorLogger.success('用户 ' + username + ' 登录成功', 'Auth')
        return True, '登录成功'

    @staticmethod
    def logout():
        """退出登录"""
        username = session.get('username', 'unknown')
        # pop 第二个参数 None 是默认值，键不存在时不报错
        session.pop('logged_in', None)
        session.pop('username', None)
        ColorLogger.info('用户 ' + username + ' 登出', 'Auth')

    @staticmethod
    def is_logged_in():
        """检查是否已登录"""
        # 只要 session 里有 logged_in 字段就算登录
        return 'logged_in' in session

    @staticmethod
    def get_current_user():
        """获取当前登录的用户名"""
        return session.get('username')

    @staticmethod
    def change_password(old_password, new_password):
        """修改密码，返回 (是否成功, 消息)"""
        if not AuthService.is_logged_in():
            return False, '未登录'

        # 验证旧密码
        # 必须先确认是本人，否则任何人都能改密码
        from utils.password import verify_password, hash_password
        if not verify_password(old_password, Config.PASSWORD_SALT, Config.ADMIN_PASSWORD):
            return False, '旧密码不正确'

        # 验证新密码强度
        # 防止用户设置弱密码（如 123456）
        valid, message = validate_password(new_password)
        if not valid:
            return False, message

        # 更新密码
        # 每次改密码都重新生成盐值，这样即使新密码和旧密码一样，
        # 哈希值也不同，攻击者无法通过对比哈希值判断密码是否改过
        salt, password_hash = hash_password(new_password)
        Config.PASSWORD_SALT = salt
        Config.ADMIN_PASSWORD = password_hash
        ColorLogger.info('密码修改成功', 'Auth')
        return True, '密码修改成功'
