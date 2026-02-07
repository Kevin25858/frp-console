"""
FRP Console 主应用文件
纯配置管理架构 - 不管理 frpc 进程
"""
import os
import sys
from flask import Flask, session, render_template, g, request, jsonify
from flask_socketio import SocketIO, emit, disconnect

# 添加 app 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和工具
from config import Config
from utils.logger import ColorLogger
from models.database import init_db, get_db, close_db

# 导入蓝图
from api.routes.auth import auth_bp
from api.routes.clients import clients_bp
from api.routes.admin import admin_bp
from api.routes.audit import audit_bp
from api.routes.users import users_bp
from api.routes.service import service_bp


def create_app(testing=False):
    """
    创建 Flask 应用的工厂函数

    Args:
        testing: 是否为测试模式

    Returns:
        Flask 应用实例
    """
    # 创建 Flask 应用
    app_instance = Flask(
        __name__,
        static_folder='../frontend/dist',
        static_url_path='/static'
    )

    # 配置应用
    app_instance.secret_key = Config.SECRET_KEY
    app_instance.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
    app_instance.config['SESSION_REFRESH_EACH_REQUEST'] = Config.SESSION_REFRESH_EACH_REQUEST
    app_instance.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    app_instance.config['SESSION_COOKIE_HTTPONLY'] = True
    
    # 启用 HTTPS only cookies（仅当明确要求）
    force_https = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    if force_https:
        app_instance.config['SESSION_COOKIE_SECURE'] = True
        ColorLogger.info('已启用 SESSION_COOKIE_SECURE (HTTPS only)', 'Security')
    else:
        app_instance.config['SESSION_COOKIE_SECURE'] = False

    if testing:
        app_instance.config['TESTING'] = True
        # 测试模式下禁用 HTTPS only cookies
        app_instance.config['SESSION_COOKIE_SECURE'] = False

    # 注册数据库关闭函数
    app_instance.teardown_appcontext(close_db)

    # 注册蓝图
    app_instance.register_blueprint(auth_bp)
    app_instance.register_blueprint(clients_bp)
    app_instance.register_blueprint(admin_bp)
    app_instance.register_blueprint(audit_bp)
    app_instance.register_blueprint(users_bp)
    app_instance.register_blueprint(service_bp)

    # SPA Catch-all Route
    @app_instance.route("/", defaults={"path": ""})
    @app_instance.route("/<path:path>")
    def serve_spa(path):
        """SPA 路由支持 - 所有非 API 请求都返回 index.html"""
        # API 请求不应该走这里，但做个保险
        if path.startswith('api/'):
            return jsonify({'error': 'Not Found'}), 404

        # 静态文件请求
        if path.startswith('static/'):
            file_path = path[7:]  # 去掉 'static/' 前缀
            full_path = os.path.join(app_instance.static_folder, file_path)
            if os.path.exists(full_path):
                return app_instance.send_static_file(file_path)

        # 其他所有请求返回 index.html，让前端路由处理
        return app_instance.send_static_file("index.html")

    return app_instance


# 创建全局应用实例（用于非测试环境）
app = create_app()

# 初始化 SocketIO
# 从环境变量读取允许的 CORS 来源，默认为同源
cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if cors_origins:
    # 支持逗号分隔的多个来源
    allowed_origins = [origin.strip() for origin in cors_origins.split(',')]
else:
    # 默认只允许同源
    allowed_origins = None  # SocketIO 默认行为

socketio = SocketIO(app, cors_allowed_origins=allowed_origins or "*", async_mode='threading')

if allowed_origins:
    ColorLogger.info(f'CORS 限制为: {allowed_origins}', 'Security')
else:
    ColorLogger.warning('CORS 未限制，允许所有来源', 'Security')


# ==================== WebSocket 事件处理 ====================
@socketio.on('connect')
def handle_connect():
    """WebSocket 连接处理"""
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket 断开处理"""
    pass


# ==================== 主程序入口 ====================
if __name__ == '__main__':
    # 初始化数据库
    init_db()

    # 运行用户表迁移
    try:
        from migrations.migrate_users import run_migrations
        run_migrations()
    except Exception as e:
        ColorLogger.warning(f"用户表迁移失败（可能已存在）: {e}", 'App')

    # 启动服务
    ColorLogger.success(f"FRP Console 启动成功，监听端口: {Config.PORT}", 'App')
    ColorLogger.info(f"访问地址: http://0.0.0.0:{Config.PORT}", 'App')
    ColorLogger.info("注意：Web 端只管理配置，frpc 需要在目标服务器独立部署", 'App')

    socketio.run(
        app,
        host='0.0.0.0',
        port=Config.PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )
