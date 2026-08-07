"""
验证器模块
包含各种数据验证函数

为什么要验证输入：
    1. 防止脏数据进数据库（比如空名字、超长字符串）
    2. 防止恶意输入（比如配置里塞恶意脚本）
    3. 早失败早反馈：用户提交时立刻告诉哪里错了，比后续报错好

为什么用纯函数而不是类：
    验证函数没有状态，输入相同输出就相同。
    纯函数易于测试、易于组合，不需要面向对象的封装。
"""
import re

# Python 3.11+ 使用内置 tomllib，否则使用 tomli
# tomllib 是 Python 3.11 才加入的标准库，低版本要装第三方包 tomli
# 这里的 try/except 是兼容两种情况的常见写法
try:
    import tomllib
except ImportError:
    import tomli as tomllib


def validate_password(password):
    """
    验证密码强度

    参数:
        password: 要验证的密码

    返回:
        (是否有效, 错误消息)

    为什么只检查长度：
        本项目是单用户管理控制台，密码策略可以简单些。
        强密码策略（必须包含大小写数字特殊字符）反而让用户倾向于
        把密码写在便签上，安全性反而下降。
    """
    if not password:
        return False, '密码不能为空'

    if len(password) < 8:
        return False, '密码长度至少为 8 个字符'

    return True, ''


def validate_port(port):
    """
    验证端口号是否合法

    参数:
        port: 端口号

    返回:
        (是否有效, 错误消息)

    端口范围说明：
        0-1023   是知名端口（well-known），通常需要 root 权限
        1024-49151 是注册端口
        49152-65535 是动态端口
        这里允许 1-65535，让用户自由选择。
    """
    if not isinstance(port, int):
        return False, '端口号必须是整数'

    if port < 1 or port > 65535:
        return False, '端口号必须在 1-65535 范围内'

    return True, ''


def validate_client_name(name):
    """
    验证客户端名称是否合法

    参数:
        name: 客户端名称

    返回:
        (是否有效, 错误消息)
    """
    if not name or not name.strip():
        return False, '客户端名称不能为空'

    name = name.strip()

    # 检查长度
    # 限制 100 字符防止过长字符串撑爆 UI 或数据库
    if len(name) > 100:
        return False, '客户端名称不能超过 100 个字符'

    # 只允许字母、数字、下划线、连字符和中文
    # 正则解释：
    #   ^         字符串开头
    #   [...]     字符集合
    #   a-zA-Z0-9 字母和数字
    #   _         下划线
    #   \-        连字符（在字符集里要转义或放最后）
    #   \u4e00-\u9fa5  中文 Unicode 范围
    #   +         至少一个字符
    #   $         字符串结尾
    if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$', name):
        return False, '客户端名称只能包含字母、数字、下划线、连字符和中文'

    return True, ''


def _check_frpc_required_fields(config):
    """
    检查 frpc 配置是否包含必需的字段
    支持两种格式：
    - 新版 TOML：[common] 节 + [[proxies]] 节
    - 旧版 flat：顶层 serverAddr/serverPort + [proxy] 节

    参数:
        config: 解析后的配置字典

    返回:
        (是否有效, 错误消息)

    为什么兼容多种格式：
        frpc 配置格式随版本演进过：
          旧版（v0.51 之前）用 [common] + [proxy]
          新版（v0.52+）用顶层 + [[proxies]]
        用户可能从网上抄各种模板，都要能识别。
    """
    # 先从 [common] 节找服务器地址和端口
    common = config.get('common', {})
    server_addr = common.get('serverAddr')
    if not server_addr:
        server_addr = common.get('server_addr')
    server_port = common.get('serverPort')
    if not server_port:
        server_port = common.get('server_port')

    # 如果 [common] 里没有，从顶层找（旧版格式）
    if not server_addr:
        server_addr = config.get('serverAddr')
        if not server_addr:
            server_addr = config.get('server_addr')
    if not server_port:
        server_port = config.get('serverPort')
        if not server_port:
            server_port = config.get('server_port')

    if not server_addr:
        return False, '配置缺少 serverAddr（FRP 服务器地址）'

    if not server_port:
        return False, '配置缺少 serverPort（FRP 服务器端口）'

    # 验证端口号
    # 配置里的端口可能是字符串，要转成 int 检查范围
    try:
        port = int(server_port)
        if port < 1 or port > 65535:
            return False, 'serverPort 无效: ' + str(server_port) + '，必须是 1-65535 之间的整数'
    except (ValueError, TypeError):
        return False, 'serverPort 无效: ' + str(server_port) + '，必须是整数'

    # 检查是否有至少一个代理配置
    # 没有代理的 frpc 配置没意义（什么都不转发）
    has_proxy = False

    # 新版：[[proxies]] 是列表
    proxies = config.get('proxies', [])
    if isinstance(proxies, list) and len(proxies) > 0:
        has_proxy = True

    # 旧版：[proxy] 节
    if not has_proxy:
        proxy = config.get('proxy', {})
        if isinstance(proxy, dict):
            if 'type' in proxy or 'localPort' in proxy or 'remotePort' in proxy:
                has_proxy = True

    # 遍历所有节查找代理配置
    # 这是为了兼容一些非标准格式（用户自定义的节名）
    if not has_proxy:
        # 这些键不是代理配置，跳过
        skip_keys = {'common', 'serverAddr', 'server_addr', 'serverPort', 'server_port',
                     'auth', 'transport', 'user', 'meta', 'include', 'proxies', 'proxy'}
        for key in config:
            if key in skip_keys:
                continue
            value = config[key]
            if isinstance(value, dict):
                # 如果某个节里有 type/localPort/remotePort，认为是代理
                if 'type' in value or 'localPort' in value or 'remotePort' in value:
                    has_proxy = True
                    break

    if not has_proxy:
        return False, '配置缺少代理规则（如 [[proxies]] 节）'

    return True, ''


def validate_toml_config(config):
    """
    验证 TOML 配置格式是否正确

    参数:
        config: 配置字符串

    返回:
        (是否有效, 错误消息)

    验证流程：
        1. 非空检查
        2. TOML 语法解析
        3. frpc 必需字段检查
    这样分层验证便于定位问题。
    """
    if not config or not config.strip():
        return False, '配置不能为空'

    # 尝试用 TOML 解析器解析
    try:
        parsed_config = tomllib.loads(config)
    except tomllib.TOMLDecodeError as e:
        # TOML 语法错误（比如引号没闭合）
        return False, 'TOML 格式错误: ' + str(e)
    except Exception as e:
        # 其他意外错误
        return False, '配置解析失败: ' + str(e)

    # 检查是否为空配置
    # 解析成功但内容为空也算无效
    if not parsed_config:
        return False, '配置不能为空对象'

    # 检查 frpc 必需的字段
    is_valid, error_msg = _check_frpc_required_fields(parsed_config)
    if not is_valid:
        return False, error_msg

    return True, ''
