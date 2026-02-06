"""
验证器模块
包含各种数据验证函数
"""

import re
from typing import Tuple, Optional


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


def validate_toml_config(config: str) -> Tuple[bool, str]:
    """
    验证 TOML/INI 配置格式

    Args:
        config: 配置字符串

    Returns:
        (是否有效, 错误消息)
    """
    if not config or not config.strip():
        return False, '配置不能为空'

    # 基本格式检查
    lines = config.strip().split('\n')
    has_section = False

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue

        # 检查节标题格式 [section] 或 [[section]]
        if line.startswith('[') and line.endswith(']'):
            has_section = True
            continue

        # 检查键值对格式 key = value
        # 支持以下格式:
        #   key = "value"
        #   key = 123
        #   key = true
        #   key = ["array"]
        #   key = {table}
        if '=' not in line:
            # 可能是内联表的一部分，跳过
            continue

        key_part = line.split('=')[0].strip()
        if not key_part:
            return False, f'第 {line_num} 行格式错误: 键名不能为空'

    if not has_section:
        return False, '配置必须至少包含一个 [section] 节'

    return True, ''


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
