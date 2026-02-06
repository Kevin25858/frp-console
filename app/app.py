"""
FRP Console 主应用文件
重构后的模块化架构
"""
import os
import sys
import time
import threading
from flask import Flask, session, render_template, g, request, jsonify
from flask_socketio import SocketIO, emit, disconnect

# 添加 app 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和工具
from config import Config
from utils.logger import ColorLogger
from utils.helpers import check_restart_limit, record_restart
from models.database import init_db, get_db, get_db_connection, close_db

# 导入服务
from services.client_service import ClientService
from services.process_service import ProcessService
from services.alert_service import AlertService
from services.auth_service import AuthService

# 导入蓝图
from api.routes.auth import auth_bp
from api.routes.clients import clients_bp
from api.routes.admin import admin_bp
from api.routes.audit import audit_bp
from api.routes.users import users_bp


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
    
    # 生产环境启用 HTTPS only cookies
    # 通过环境变量判断是否启用 HTTPS
    is_production = os.environ.get('FLASK_ENV') == 'production'
    force_https = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    if is_production or force_https:
        app_instance.config['SESSION_COOKIE_SECURE'] = True
        ColorLogger.info('已启用 SESSION_COOKIE_SECURE (HTTPS only)', 'Security')

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

# WebSocket 客户端集合（监控功能已移除）
websocket_clients = set()


# ==================== WebSocket 事件处理 ====================
@socketio.on('connect')
def handle_connect():
    """WebSocket 连接处理"""
    websocket_clients.add(request.sid)
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket 断开处理"""
    websocket_clients.discard(request.sid)


# ==================== 健康检查线程 ====================
def try_restart_frpc(client_id, client_name, config_path, force=False):
    """
    尝试重启 frpc 客户端，带频率限制防止无限重启

    Args:
        client_id: 客户端 ID
        client_name: 客户端名称
        config_path: 配置文件路径
        force: 是否强制重启（忽略频率限制）

    Returns:
        是否重启成功
    """
    now = time.time()

    # 获取或初始化重启记录
    from utils.helpers import restart_records
    if client_id not in restart_records:
        restart_records[client_id] = {
            'count': 0,
            'last_restart': 0,
            'first_failure': now,
            'consecutive_failures': 0,
            'last_success': now
        }

    record = restart_records[client_id]

    # 如果上次成功运行已经超过5分钟，重置失败计数
    if now - record['last_success'] > Config.RESTART_WINDOW:
        record['consecutive_failures'] = 0
        record['count'] = 0

    # 检查是否在冷却期（force模式跳过冷却期）
    if not force and now - record['last_restart'] < Config.RESTART_COOLDOWN:
        ColorLogger.debug(f"客户端 {client_name} 处于冷却期，跳过重启", 'Keepalive')
        return False

    # 检查5分钟内重启次数（force模式跳过限制）
    if not force and now - record['first_failure'] < Config.RESTART_WINDOW:
        if record['count'] >= Config.MAX_RESTARTS_PER_WINDOW:
            # 超过限制，发送告警并停止尝试
            if record['consecutive_failures'] == Config.MAX_RESTARTS_PER_WINDOW:
                AlertService.send_alert(
                    client_name,
                    'restart_limit',
                    f'FRP客户端 {client_name} 5分钟内重启超过{Config.MAX_RESTARTS_PER_WINDOW}次，已停止自动重启'
                )
            record['consecutive_failures'] += 1
            return False
    else:
        # 超过窗口期，重置计数
        record['count'] = 0
        record['first_failure'] = now
        record['consecutive_failures'] = 0

    # 执行重启
    ColorLogger.warning(f"正在重启客户端 {client_name} (第{record['count']+1}次/{Config.MAX_RESTARTS_PER_WINDOW}次)", 'Keepalive')
    success, message = ProcessService.restart_frpc(client_id, client_name, config_path, force)

    if success:
        record['last_restart'] = now
        record['count'] += 1
        record['last_success'] = now
        ColorLogger.success(f"客户端 {client_name} 重启成功", 'Keepalive')

        # 记录重启事件到数据库
        try:
            db = get_db()
            db.execute('''
                INSERT INTO logs (client_id, level, message, created_at)
                VALUES (?, 'INFO', ?, ?)
            ''', (client_id, f'自动重启成功 (第{record["count"]}次/5分钟)', time.strftime('%Y-%m-%d %H:%M:%S')))
            db.commit()
        except Exception:
            pass

        return True
    else:
        record['consecutive_failures'] += 1
        ColorLogger.error(f"客户端 {client_name} 重启失败: {message}", 'Keepalive')
        return False


def health_check():
    """健康检查线程"""
    last_failed_check = {}  # 记录上次检测失败的客户端时间

    while True:
        db = None
        try:
            db = get_db_connection()

            # 首先处理 always_on 客户端（最高优先级）
            always_on_clients = db.execute(
                'SELECT * FROM clients WHERE enabled = 1 AND always_on = 1'
            ).fetchall()

            for client in always_on_clients:
                client_id = client['id']
                client_name = client['name']
                config_path = client['config_path']

                # 使用 is_frpc_running 检查进程是否存在
                is_running = ProcessService.is_frpc_running(client_id, config_path)

                # 如果 always_on 客户端没有运行，强制启动
                if not is_running:
                    now = time.time()
                    # 检查是否在冷却期内（避免频繁重启）
                    if client_id in last_failed_check:
                        time_since_last_fail = now - last_failed_check[client_id]
                        if time_since_last_fail < 60:  # 60秒内不重复重启
                            continue

                    ColorLogger.warning(f"always_on 客户端 {client_name} 未运行，强制启动", 'HealthCheck')
                    db.execute("UPDATE clients SET status = 'stopped' WHERE id = ?", (client_id,))
                    db.commit()

                    # 强制重启（忽略频率限制）
                    restart_success = try_restart_frpc(client_id, client_name, config_path, force=True)
                    last_failed_check[client_id] = now

                    if not restart_success:
                        # 立即发送告警
                        AlertService.send_alert(
                            client_name,
                            'always_on_failed',
                            f'always_on 客户端 {client_name} 启动失败，需要立即检查'
                        )

            # 然后处理普通客户端（非 always_on）
            # 普通客户端不会自动重启，只更新状态
            normal_clients = db.execute(
                'SELECT * FROM clients WHERE enabled = 1 AND always_on = 0'
            ).fetchall()

            for client in normal_clients:
                client_id = client['id']
                client_name = client['name']
                config_path = client['config_path']

                # 使用 is_frpc_running 检查进程状态
                is_running = ProcessService.is_frpc_running(client_id, config_path)

                if not is_running:
                    # 进程未运行，只更新状态，不自动重启
                    if client['status'] == 'running':
                        db.execute("UPDATE clients SET status = 'stopped' WHERE id = ?", (client_id,))
                        db.commit()
                        ColorLogger.info(f"客户端 {client_name} 已停止", 'HealthCheck')

        except Exception as e:
            ColorLogger.error(f"健康检查错误: {e}", 'HealthCheck')
        finally:
            # 关闭数据库连接
            if db:
                try:
                    db.close()
                except:
                    pass

        time.sleep(Config.HEALTH_CHECK_INTERVAL)


# ==================== 主程序入口 ====================
if __name__ == '__main__':
    # 检查端口是否被占用
    from services.process_service import ProcessService
    if not ProcessService.check_port_available(Config.PORT):
        ColorLogger.error(
            f"端口 {Config.PORT} 已被占用，请先停止占用该端口的程序或使用其他端口",
            'App'
        )
        import sys
        sys.exit(1)

    # 初始化数据库
    init_db()

    # 运行用户表迁移
    try:
        from migrations.migrate_users import run_migrations
        run_migrations()
    except Exception as e:
        ColorLogger.warning(f"用户表迁移失败（可能已存在）: {e}", 'App')

    # 启动健康检查线程
    try:
        health_thread = threading.Thread(target=health_check, daemon=True)
        health_thread.start()
        ColorLogger.success("健康检查线程已启动", 'App')
    except Exception as e:
        ColorLogger.error(f"启动健康检查线程失败: {e}", 'App')

    # 启动服务
    ColorLogger.success(f"FRP Console 启动成功，监听端口: {Config.PORT}", 'App')
    ColorLogger.info(f"访问地址: http://0.0.0.0:{Config.PORT}", 'App')

    socketio.run(
        app,
        host='0.0.0.0',
        port=Config.PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )