"""
认证相关路由

什么是路由（Route）：
    路由是 URL 到处理函数的映射。
    用户访问 /login，Flask 就调用 login() 函数处理。

什么是蓝图（Blueprint）：
    蓝图是一组路由的集合，可以整体注册到 app。
    好处：
      1. 把相关路由放一起，便于维护
      2. 可以加统一的预处理（如全部要求登录）
      3. 大项目可以拆分成多个蓝图模块

什么是 REST 风格：
    用 HTTP 方法表示操作意图：
      GET    = 读取（不改数据）
      POST   = 创建
      PUT    = 更新
      DELETE = 删除
    本项目混合用了 REST 和传统表单风格（/login 用 POST 表单）
"""
from flask import Blueprint, request, jsonify, session, redirect, current_app

from services.auth_service import AuthService

# 创建蓝图对象
# 第一个参数是蓝图名字，第二个是模块名（用于定位资源）
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/csrf-token')
def csrf_token():
    """
    获取 CSRF token

    为什么需要这个接口：
        前端要做写操作（POST/PUT/DELETE）前，先调这个接口拿 token，
        然后把 token 放在请求头里带上。
        服务端校验 token 正确才允许写操作，防止 CSRF 攻击。
    """
    return jsonify({'csrf_token': AuthService.get_csrf_token()})


@auth_bp.route('/api/me')
def me():
    """
    获取当前用户信息

    用途：
        前端刷新页面时调这个接口，判断是否还在登录态。
        如果未登录返回 401，前端跳转到登录页。
    """
    if not AuthService.is_logged_in():
        # 401 Unauthorized：未认证
        # 前端收到 401 会跳转登录页
        return jsonify({'authenticated': False}), 401
    return jsonify({
        'authenticated': True,
        'username': session.get('username'),
    })


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    登录页面和登录处理

    为什么一个路由处理 GET 和 POST：
        GET  显示登录页（返回 HTML）
        POST 处理登录表单提交
        这样前端只需要一个 /login URL，简化逻辑
    """
    # 已登录则跳转首页
    # 避免已登录用户又看到登录页
    if AuthService.is_logged_in():
        return redirect('/')

    if request.method == 'POST':
        # 支持 JSON 和表单两种提交方式
        # 前端用 fetch 调用就是 JSON，用 <form> 提交就是表单
        # 这里都兼容，方便不同前端实现
        data = request.get_json(silent=True)
        if not data:
            # silent=True：JSON 解析失败不报错，返回 None
            # 走到这说明不是 JSON 请求，按表单处理
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
        else:
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

        # .strip() 去掉首尾空格，防止用户误输入空格导致登录失败

        success, message = AuthService.login(username, password)

        if success:
            if request.is_json:
                # JSON 请求返回 JSON
                return jsonify({'message': message})
            # 表单请求重定向到首页
            # 302 重定向让浏览器跳转到 /
            return redirect('/')
        else:
            if request.is_json:
                return jsonify({'error': message}), 401
            # 表单提交失败返回 401 + 纯文本
            return 'Invalid username or password.', 401

    # GET 请求返回前端页面
    # 这里返回 SPA 的 index.html，让 React 渲染登录页
    return current_app.send_static_file('index.html')


@auth_bp.route('/logout')
def logout():
    """退出登录"""
    AuthService.logout()
    # 登出后跳回登录页
    return redirect('/login')


@auth_bp.route('/api/change-password', methods=['POST'])
def change_password():
    """修改密码"""
    if not AuthService.is_logged_in():
        return jsonify({'error': '未登录'}), 401

    # 获取 CSRF token（从请求头或请求体中）
    # 改密码是敏感操作，必须验证 CSRF
    token = request.headers.get('X-CSRF-Token')
    if not token and request.is_json:
        token = request.json.get('csrf_token')

    if not AuthService.verify_csrf_token(token):
        # 403 Forbidden：禁止访问（认证了但没权限做这个操作）
        return jsonify({'error': 'CSRF 验证失败'}), 403

    data = request.get_json() or {}
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()

    success, message = AuthService.change_password(old_password, new_password)
    if success:
        return jsonify({'message': message})
    # 400 Bad Request：请求参数有问题
    return jsonify({'error': message}), 400
