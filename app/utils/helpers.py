"""
辅助工具模块
包含各种辅助函数

注意：本模块使用内存中的全局字典存储状态（login_attempts, restart_records）。
这种设计在以下场景存在限制：
1. 多进程部署时状态不共享
2. 应用重启后数据丢失
3. 无法水平扩展

如需支持上述场景，建议将状态存储迁移到 Redis 或数据库。
"""
import time
from typing import Dict, Tuple
from utils.logger import ColorLogger


# 登录速率限制记录（内存存储，重启后丢失）
# TODO: 如需多实例部署，请迁移到 Redis
login_attempts: Dict[str, Dict[str, int]] = {}  # IP -> {'count': int, 'locked_until': timestamp}


def check_login_rate_limit(ip: str, max_attempts: int = 5, lockout_time: int = 900) -> Tuple[bool, str]:
    """
    检查登录频率限制

    Args:
        ip: 客户端 IP 地址
        max_attempts: 最大尝试次数
        lockout_time: 锁定时间（秒）

    Returns:
        (是否允许, 错误消息)
    """
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': 0}

    record = login_attempts[ip]

    # 如果锁定时间已过，重置计数
    if now > record['locked_until']:
        record['count'] = 0
        record['locked_until'] = 0

    # 检查是否被锁定
    if now < record['locked_until']:
        remaining = int(record['locked_until'] - now)
        return False, f'登录失败次数过多，请等待 {remaining} 秒后重试'

    return True, ''


def record_login_attempt(ip: str, success: bool, max_attempts: int = 5, lockout_time: int = 900) -> None:
    """
    记录登录尝试

    Args:
        ip: 客户端 IP 地址
        success: 是否登录成功
        max_attempts: 最大尝试次数
        lockout_time: 锁定时间（秒）
    """
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': 0}

    record = login_attempts[ip]

    if success:
        # 登录成功，重置计数
        record['count'] = 0
        record['locked_until'] = 0
    else:
        # 登录失败，增加计数
        record['count'] += 1
        if record['count'] >= max_attempts:
            record['locked_until'] = now + lockout_time
            ColorLogger.warning(f'登录失败过多，IP {ip} 已被锁定 {lockout_time} 秒', 'Security')


# 重启记录（内存存储，重启后丢失）
# TODO: 如需多实例部署，请迁移到 Redis
restart_records: Dict[int, Dict[str, int]] = {}  # client_id -> {'count': int, 'last_restart': int, ...}


def check_restart_limit(client_id: int, max_restarts: int = 3, window: int = 300, cooldown: int = 10, force: bool = False) -> Tuple[bool, str]:
    """
    检查重启频率限制

    Args:
        client_id: 客户端 ID
        max_restarts: 最大重启次数
        window: 时间窗口（秒）
        cooldown: 重启间隔（秒）
        force: 是否强制重启（忽略限制）

    Returns:
        (是否允许, 错误消息)
    """
    if force:
        return True, ''

    now = time.time()
    if client_id not in restart_records:
        restart_records[client_id] = {
            'count': 0,
            'last_restart': 0,
            'first_failure': 0,
            'consecutive_failures': 0
        }

    record = restart_records[client_id]

    # 检查冷却时间
    if now - record['last_restart'] < cooldown:
        remaining = int(cooldown - (now - record['last_restart']))
        return False, f'重启过于频繁，请等待 {remaining} 秒后重试'

    # 检查时间窗口内的重启次数
    if now - record['first_failure'] > window:
        # 超出时间窗口，重置计数
        record['count'] = 0
        record['first_failure'] = 0

    if record['count'] >= max_restarts:
        return False, f'{window} 秒内重启次数已达上限 ({max_restarts} 次)'

    return True, ''


def record_restart(client_id: int, success: bool = True) -> None:
    """
    记录重启

    Args:
        client_id: 客户端 ID
        success: 是否重启成功
    """
    now = time.time()
    if client_id not in restart_records:
        restart_records[client_id] = {
            'count': 0,
            'last_restart': 0,
            'first_failure': 0,
            'consecutive_failures': 0
        }

    record = restart_records[client_id]
    record['last_restart'] = now

    if success:
        record['consecutive_failures'] = 0
    else:
        record['count'] += 1
        record['consecutive_failures'] += 1
        if record['first_failure'] == 0:
            record['first_failure'] = now


def reset_restart_record(client_id: int) -> None:
    """
    重置重启记录

    Args:
        client_id: 客户端 ID
    """
    if client_id in restart_records:
        del restart_records[client_id]