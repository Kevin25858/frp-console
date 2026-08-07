"""
辅助工具模块
登录速率限制功能

什么是速率限制：
    限制某个 IP 在一段时间内能尝试登录的次数。
    防止攻击者用字典暴力破解密码。

为什么按 IP 限制而不是按用户名：
    1. 本项目是单用户，按用户名限制没意义
    2. 攻击者可能用同一个 IP 试多个用户名
    3. 按 IP 限制能直接封锁攻击来源

为什么用内存字典而不是数据库：
    1. 速率限制是临时状态，重启后重置无伤大雅
    2. 内存读写快，不增加数据库压力
    3. 单机部署不需要跨进程共享
"""
import time
from utils.logger import ColorLogger


# 登录失败记录：{IP地址: {count: 失败次数, locked_until: 锁定截止时间}}
# 用字典存在内存里，进程重启会清空（可接受）
login_attempts = {}


def check_login_rate_limit(ip, max_attempts=5, lockout_time=900):
    """
    检查某个 IP 是否还能尝试登录

    参数:
        ip:           客户端 IP 地址
        max_attempts: 最多允许失败几次
        lockout_time: 锁定多长时间（秒）

    返回:
        (是否允许, 错误消息)
    """
    now = time.time()

    # 如果这个 IP 没有记录过，初始化一条
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': 0}

    record = login_attempts[ip]

    # 如果锁定时间已过，重置计数
    # locked_until 是锁定截止的时间戳
    # now > locked_until 表示已经过了锁定期
    if record['locked_until'] > 0 and now > record['locked_until']:
        record['count'] = 0
        record['locked_until'] = 0

    # 如果还在锁定期内，拒绝登录
    if now < record['locked_until']:
        # 计算还剩多少秒解锁，给用户明确提示
        remaining = int(record['locked_until'] - now)
        return False, '登录失败次数过多，请等待 ' + str(remaining) + ' 秒后重试'

    return True, ''


def record_login_attempt(ip, success, max_attempts=5, lockout_time=900):
    """
    记录一次登录尝试

    参数:
        ip:           客户端 IP 地址
        success:      本次登录是否成功
        max_attempts: 最多允许失败几次
        lockout_time: 锁定多长时间（秒）
    """
    now = time.time()

    # 如果这个 IP 没有记录过，初始化一条
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'locked_until': 0}

    record = login_attempts[ip]

    if success:
        # 登录成功，重置计数
        # 这样用户偶尔输错一次不会累积影响
        record['count'] = 0
        record['locked_until'] = 0
    else:
        # 登录失败，计数加一
        record['count'] += 1

        # 失败次数达到上限，锁定
        if record['count'] >= max_attempts:
            # now + lockout_time 是锁定截止的时间戳
            record['locked_until'] = now + lockout_time
            ColorLogger.warning(
                '登录失败过多，IP ' + ip + ' 已被锁定 ' + str(lockout_time) + ' 秒',
                'Security'
            )
