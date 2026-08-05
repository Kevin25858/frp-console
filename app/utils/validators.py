"""
验证器模块
包含各种数据验证函数
"""
import sys
import re
from typing import Tuple, Optional, Dict, Any

# Python 3.11+ 使用内置 tomllib，否则使用 tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib


def validate_password(password: str) -> Tuple[bool, str]:
    """
    验证密码强度

    Args:
        password: 要验证的密码

    Returns:
        (是否有效, 错误消息)
    """
    if not password:
        return False, '密码不能为空'

    if len(password) < 8:
        return False, '密码长度至少为 8 个字符'

    # 可选：添加更复杂的密码验证
    # if not re.search(r'[A-Z]', password):
    #     return False, '密码必须包含至少一个大写字母'
    # if not re.search(r'[a-z]', password):
    #     return False, '密码必须包含至少一个小写字母'
    # if not re.search(r'\d', password):
    #     return False, '密码必须包含至少一个数字'
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     return False, '密码必须包含至少一个特殊字符'

    return True, ''


def validate_email(email: str) -> Tuple[bool, str]:
    """
    验证邮箱格式

    Args:
        email: 要验证的邮箱地址

    Returns:
        (是否有效, 错误消息)
    """
    if not email:
        return True, ''  # 允许为空

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, '邮箱格式不正确'

    return True, ''


def validate_port(port: int) -> Tuple[bool, str]:
    """
    验证端口号

    Args:
        port: 端口号

    Returns:
        (是否有效, 错误消息)
    """
    if not isinstance(port, int):
        return False, '端口号必须是整数'

    if port < 1 or port > 65535:
        return False, '端口号必须在 1-65535 范围内'

    return True, ''


def validate_client_name(name: str) -> Tuple[bool, str]:
    """
    验证客户端名称

    Args:
        name: 客户端名称

    Returns:
        (是否有效, 错误消息)
    """
    if not name or not name.strip():
        return False, '客户端名称不能为空'

    name = name.strip()

    # 检查长度
    if len(name) > 100:
        return False, '客户端名称不能超过 100 个字符'

    # 检查特殊字符
    if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$', name):
        return False, '客户端名称只能包含字母、数字、下划线、连字符和中文'

    return True, ''


def validate_server_addr(addr: str) -> Tuple[bool, str]:
    """
    验证服务器地址

    Args:
        addr: 服务器地址

    Returns:
        (是否有效, 错误消息)
    """
    if not addr or not addr.strip():
        return True, ''  # 允许为空

    addr = addr.strip()

    # 可以是域名或 IP 地址
    domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])*$'
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'

    if not re.match(domain_pattern, addr) and not re.match(ip_pattern, addr):
        return False, '服务器地址格式不正确'

    return True, ''


def _check_frpc_required_fields(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    检查 frpc 配置是否包含必需的字段。
    支持两种格式：
    - 新版 TOML：[common] 节 + [[proxies]] 节
    - 旧版 flat：顶层 serverAddr/serverPort + [proxy] 节
    """
    # 检查 [common] 节（新版 TOML 格式）
    common = config.get('common', {})
    server_addr = common.get('serverAddr') or common.get('server_addr')
    server_port = common.get('serverPort') or common.get('server_port')

    # 如果 [common] 里没有，检查顶层（旧版 flat 格式）
    if not server_addr:
        server_addr = config.get('serverAddr') or config.get('server_addr')
    if not server_port:
        server_port = config.get('serverPort') or config.get('server_port')

    if not server_addr:
        return False, '配置缺少 serverAddr（FRP 服务器地址）'

    if not server_port:
        return False, '配置缺少 serverPort（FRP 服务器端口）'

    # 验证端口号
    try:
        port = int(server_port)
        if port < 1 or port > 65535:
            return False, f'serverPort 无效: {server_port}，必须是 1-65535 之间的整数'
    except (ValueError, TypeError):
        return False, f'serverPort 无效: {server_port}，必须是整数'

    # 检查是否有至少一个代理配置
    has_proxy = False

    # 新版：[[proxies]] 是列表
    proxies = config.get('proxies', [])
    if isinstance(proxies, list) and len(proxies) > 0:
        has_proxy = True

    # 旧版：[proxy] 节
    if not has_proxy:
        proxy = config.get('proxy', {})
        if isinstance(proxy, dict) and ('type' in proxy or 'localPort' in proxy or 'remotePort' in proxy):
            has_proxy = True

    # 遍历所有节查找代理配置
    if not has_proxy:
        skip_keys = {'common', 'serverAddr', 'server_addr', 'serverPort', 'server_port',
                     'auth', 'transport', 'user', 'meta', 'include', 'proxies', 'proxy'}
        for key, value in config.items():
            if key in skip_keys:
                continue
            if isinstance(value, dict):
                if 'type' in value or 'localPort' in value or 'remotePort' in value:
                    has_proxy = True
                    break

    if not has_proxy:
        return False, '配置缺少代理规则（如 [[proxies]] 节）'

    return True, ''


def _check_frpc_deprecated_options(config: Dict[str, Any]) -> list:
    """
    检查是否有已弃用的 FRP 配置选项

    Args:
        config: 解析后的配置字典

    Returns:
        警告信息列表
    """
    warnings = []

    # 已弃用的选项
    deprecated = {
        'authentication_method': '请使用 auth.method',
        'authenticate_heartbeats': '请使用 auth.additionalScopes',
        'authenticate_new_work_conns': '请使用 auth.additionalScopes',
    }

    def check_dict(d: Dict[str, Any], prefix: str = ''):
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key in deprecated:
                warnings.append(f'配置警告: {full_key} 已弃用，{deprecated[key]}')
            if isinstance(value, dict):
                check_dict(value, full_key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        check_dict(item, f"{full_key}[{i}]")

    check_dict(config)
    return warnings


def validate_toml_config(config: str) -> Tuple[bool, str]:
    """
    验证 TOML/INI 配置格式（使用真正的 TOML 解析器）

    Args:
        config: 配置字符串

    Returns:
        (是否有效, 错误消息)
    """
    if not config or not config.strip():
        return False, '配置不能为空'

    # 尝试解析 TOML
    try:
        parsed_config = tomllib.loads(config)
    except tomllib.TOMLDecodeError as e:
        return False, f'TOML 格式错误: {str(e)}'
    except Exception as e:
        return False, f'配置解析失败: {str(e)}'

    # 检查是否为空配置
    if not parsed_config:
        return False, '配置不能为空对象'

    # 检查 frpc 必需的字段
    is_valid, error_msg = _check_frpc_required_fields(parsed_config)
    if not is_valid:
        return False, error_msg

    return True, ''


def validate_toml_config_with_warnings(config: str) -> Tuple[bool, str, list]:
    """
    验证 TOML/INI 配置格式，并返回警告信息

    Args:
        config: 配置字符串

    Returns:
        (是否有效, 错误消息, 警告列表)
    """
    is_valid, error_msg = validate_toml_config(config)
    if not is_valid:
        return False, error_msg, []

    # 解析配置以获取警告
    try:
        parsed_config = tomllib.loads(config)
        warnings = _check_frpc_deprecated_options(parsed_config)
        return True, '', warnings
    except Exception:
        return True, '', []


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符

    Args:
        filename: 原始文件名

    Returns:
        清理后的文件名
    """
    # 移除路径遍历字符
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')

    # 移除特殊字符
    filename = re.sub(r'[<>:"|?*]', '', filename)

    # 限制长度
    if len(filename) > 255:
        filename = filename[:255]

    return filename.strip()
