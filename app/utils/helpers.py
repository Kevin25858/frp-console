"""
辅助工具模块
"""
import time
from typing import Tuple
from utils.logger import ColorLogger

# 登录速率限制记录
login_attempts = {}


def check_login_rate_limit(ip: str, max_attempts: int = 5, lockout_time: int = 900) -> Tuple[bool, str]:
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': 0}

    record = login_attempts[ip]

    if record['locked_until'] > 0 and now > record['locked_until']:
        record['count'] = 0
        record['locked_until'] = 0

    if now < record['locked_until']:
        remaining = int(record['locked_until'] - now)
        return False, f'登录失败次数过多，请等待 {remaining} 秒后重试'

    return True, ''


def record_login_attempt(ip: str, success: bool, max_attempts: int = 5, lockout_time: int = 900) -> None:
    now = time.time()
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': 0}

    record = login_attempts[ip]

    if success:
        record['count'] = 0
        record['locked_until'] = 0
    else:
        record['count'] += 1
        if record['count'] >= max_attempts:
            record['locked_until'] = now + lockout_time
            ColorLogger.warning(f'登录失败过多，IP {ip} 已被锁定 {lockout_time} 秒', 'Security')
