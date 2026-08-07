"""
FRP Console 主应用文件
基于 Docker 容器模型管理 frpc 客户端

为什么用 Flask：
    Flask 是 Python 轻量级 Web 框架，学习曲线平缓，适合中小型项目。
    本项目只需要"网页 + REST API"，不需要 Django 那样的全家桶，
    所以 Flask 是合适的选择。

什么是应用工厂（create_app）：
    把"创建应用实例"封装成一个函数，而不是在模块顶层直接创建。
    好处：
      1. 测试时可以传入不同配置（如 testing=True）创建独立实例。
      2. 多个 worker 部署时互不干扰。
      3. 避免模块导入时就产生副作用（如连接数据库）。
"""
import os
import sys
from flask import Flask, jsonify

# 把当前文件所在目录（app/）加到 Python 路径
# 这样其他模块可以用 from config import Config 这样的简短写法
# 否则就要写 from app.config import Config，路径更长
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和工具
from config import Config
from utils.logger import ColorLogger
from models.database import init_db, close_db

# 导入路由蓝图
# 蓝图（Blueprint）是 Flask 的模块化路由机制
# 把不同业务的路由拆到不同文件里，便于维护
from api.routes.auth import auth_bp
from api.routes.clients import clients_bp


def create_app(testing=False):
    """
    创建 Flask 应用（工厂函数）

    参数:
        testing: 是否为测试模式

    返回:
        Flask 应用实例
    """
    # 创建 Flask 应用
    # static_folder 指向前端构建产物目录（vite build 的输出）
    # static_url_path 是访问静态文件的 URL 前缀，这里设为 /static
    # 这样前端打包后的 JS/CSS 就能通过 /static/xxx.js 访问
    app_instance = Flask(
        __name__,
        static_folder='../frontend/dist',
        static_url_path='/static'
    )

    # 设置会话密钥
    # 密钥用来给 session cookie 签名，防止被篡改
    # 如果密钥泄露，攻击者可以伪造登录态，所以必须保密
    app_instance.secret_key = Config.SECRET_KEY

    # 会话有效期：24 小时
    # 用户登录后，cookie 会在 24 小时后过期，需要重新登录
    app_instance.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME

    # 每次请求都刷新会话过期时间
    # 这样只要用户持续操作，就不会被强制登出
    app_instance.config['SESSION_REFRESH_EACH_REQUEST'] = Config.SESSION_REFRESH_EACH_REQUEST

    # SameSite=Strict：禁止跨站请求携带 cookie
    # 这是防范 CSRF 攻击的一道防线（攻击者从别的站点发起的请求不会带上本站 cookie）
    app_instance.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

    # HttpOnly=True：禁止 JavaScript 读取 cookie
    # 这样即使页面被注入恶意脚本（XSS），也无法偷走会话 cookie
    app_instance.config['SESSION_COOKIE_HTTPONLY'] = True

    # 是否启用 HTTPS only cookies
    # 启用后，cookie 只在 HTTPS 连接下发送，防止在公共 WiFi 被中间人窃听
    # 生产环境建议开启，本地开发关掉因为通常用 HTTP
    force_https = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    if force_https:
        app_instance.config['SESSION_COOKIE_SECURE'] = True
        ColorLogger.info('已启用 SESSION_COOKIE_SECURE (HTTPS only)', 'Security')
    else:
        app_instance.config['SESSION_COOKIE_SECURE'] = False

    # 测试模式下关闭 HTTPS only
    # 因为测试通常走 HTTP，开启 Secure 会导致 cookie 不发送，测试无法维持登录态
    if testing:
        app_instance.config['TESTING'] = True
        app_instance.config['SESSION_COOKIE_SECURE'] = False

    # 注册数据库关闭函数
    # teardown_appcontext 会在每次请求结束后自动调用 close_db
    # 这样就不会出现"数据库连接没关"导致连接泄露的问题
    app_instance.teardown_appcontext(close_db)

    # 注册路由蓝图
    # 蓝图注册后，里面定义的路由才会生效
    app_instance.register_blueprint(auth_bp)
    app_instance.register_blueprint(clients_bp)

    # SPA 路由：所有非 API 请求都返回前端 index.html
    # SPA = Single Page Application（单页应用）
    # 前端用 React Router 管理页面跳转，所以后端要把所有非 API 路径
    # 都返回 index.html，让前端路由来决定显示哪个页面
    @app_instance.route("/", defaults={"path": ""})
    @app_instance.route("/<path:path>")
    def serve_spa(path):
        """SPA 路由 - 让前端路由处理页面跳转"""

        # API 请求不应该走到这里
        # 如果走到这里说明用户访问了不存在的 API 路径，返回 404
        if path.startswith('api/'):
            return jsonify({'error': 'Not Found'}), 404

        # 静态文件请求（JS、CSS 等）
        # 直接从磁盘读取并返回，让浏览器缓存这些资源
        if path.startswith('static/'):
            file_path = path[7:]  # 去掉 'static/' 前缀
            full_path = os.path.join(app_instance.static_folder, file_path)
            if os.path.exists(full_path):
                return app_instance.send_static_file(file_path)

        # 其他请求返回 index.html，让前端路由处理
        # 比如用户访问 /clients/3/edit，后端不关心，直接返回首页 HTML
        # 浏览器加载完 JS 后，React Router 会解析 URL 显示对应页面
        return app_instance.send_static_file("index.html")

    return app_instance


# 创建全局应用实例（用于非测试环境）
# 当用 gunicorn/uwsgi 部署时，会直接 import app
# 测试时则调用 create_app(testing=True) 创建独立实例
app = create_app()


# ==================== 主程序入口 ====================
if __name__ == '__main__':
    # __name__ == '__main__' 表示脚本被直接运行（而不是被 import）
    # 这样写的好处：被 import 时不会自动启动服务，避免意外执行

    # 初始化数据库（建表、迁移）
    init_db()

    # 打印启动信息
    ColorLogger.success('FRP Console 启动成功，监听端口: ' + str(Config.PORT), 'App')
    ColorLogger.info('访问地址: http://0.0.0.0:' + str(Config.PORT), 'App')
    ColorLogger.info('frpc 以 Docker 容器方式运行，由 Web 控制台通过 docker.sock 管理', 'App')

    # 启动 Flask 服务
    # debug=False：关闭调试模式，避免代码改动自动重启（生产环境要稳定）
    # 生产环境通常用 gunicorn 启动，不会走这里
    app.run(
        host='0.0.0.0',
        port=Config.PORT,
        debug=False
    )
