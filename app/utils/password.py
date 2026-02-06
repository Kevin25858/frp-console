"""
密码加密工具模块
使用 PBKDF2-HMAC-SHA256 进行密码哈希
"""

import secrets
import hashlib
from typing import Tuple


# 密码哈希配置
HASH_ALGORITHM = "sha256"
ITERATIONS = 100000  # PBKDF2 迭代次数
SALT_LENGTH = 32  # 盐长度（字节）


def hash_password(password: str) -> Tuple[str, str]:
    """
    哈希密码

    Args:
        password: 明文密码

    Returns:
        (salt, hashed_password) 元组
    """
    # 生成随机盐
    salt = secrets.token_hex(SALT_LENGTH)

    # 使用 PBKDF2-HMAC-SHA256 哈希密码
    dk = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )

    hashed_password = dk.hex()

    return salt, hashed_password


def verify_password(password: str, salt: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        password: 明文密码
        salt: 盐值
        hashed_password: 存储的哈希密码

    Returns:
        密码是否匹配
    """
    # 使用相同的参数重新哈希
    dk = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )

    computed_hash = dk.hex()

    # 使用恒定时间比较，防止时序攻击
    return secrets.compare_digest(computed_hash, hashed_password)


def generate_secure_token(length: int = 32) -> str:
    """
    生成安全随机令牌

    Args:
        length: 令牌长度（字节）

    Returns:
        十六进制令牌字符串
    """
    return secrets.token_hex(length)


def generate_password_hash_legacy(password: str) -> str:
    """
    生成旧式密码哈希（用于兼容）
    简单的 SHA256 哈希，不推荐用于新系统

    Args:
        password: 明文密码

    Returns:
        哈希密码
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


# 默认密码哈希（用于初始化）
DEFAULT_PASSWORD_HASH = hash_password("admin123")[1]