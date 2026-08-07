"""
密码加密工具模块
使用 PBKDF2-HMAC-SHA256 进行密码哈希

为什么不存明文密码：
    1. 数据库泄露时，明文密码直接暴露
    2. 用户可能在多个网站用同一个密码，一处泄露全盘沦陷
    3. 法律合规要求（如 GDPR）通常禁止存明文

为什么用 PBKDF2 而不是 MD5/SHA256：
    MD5/SHA256 太快，攻击者每秒能试几亿次，容易被暴力破解。
    PBKDF2 通过大量迭代（这里 10 万次）故意拖慢速度，
    让暴力破解成本极高。

什么是盐（salt）：
    盐是一段随机字符串，和密码拼接后再哈希。
    作用：
      1. 相同密码哈希后结果不同（防止彩虹表攻击）
      2. 攻击者要为每个密码单独算哈希，不能批量破解
"""
import secrets
import hashlib


# 密码哈希配置
HASH_ALGORITHM = "sha256"
ITERATIONS = 100000  # PBKDF2 迭代次数（越大越安全，但越慢）
SALT_LENGTH = 32     # 盐的长度（字节）


def hash_password(password):
    """
    把明文密码加密成不可逆的哈希值

    参数:
        password: 明文密码

    返回:
        (盐值, 哈希密码) 两个字符串
    """
    # 生成随机盐值（每次不一样，防止彩虹表攻击）
    # token_hex 返回十六进制字符串，长度是字节数的 2 倍
    salt = secrets.token_hex(SALT_LENGTH)

    # 用 PBKDF2 算法哈希密码
    # 参数：算法、密码、盐、迭代次数
    # 返回的是 bytes 对象
    dk = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )

    # 转成十六进制字符串存储
    # bytes 对象不能直接存数据库，转成 hex 字符串方便存储
    hashed_password = dk.hex()

    return salt, hashed_password


def verify_password(password, salt, hashed_password):
    """
    验证密码是否正确

    参数:
        password:       用户输入的明文密码
        salt:           存储的盐值
        hashed_password: 存储的哈希密码

    返回:
        True 表示密码正确，False 表示错误

    原理：
        用相同的盐值和参数重新哈希用户输入的密码，
        如果结果和存储的哈希值一样，说明密码正确。
        （因为哈希是单向的，无法反推，只能正向验证）
    """
    # 用相同的盐值和参数重新哈希用户输入的密码
    dk = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )

    computed_hash = dk.hex()

    # 用恒定时间比较，防止时序攻击
    # 普通的 == 比较会在第一个不同的字符就返回，
    # 攻击者通过测量响应时间可以逐字符猜解密码哈希。
    # compare_digest 无论哪里不同耗时都一样。
    return secrets.compare_digest(computed_hash, hashed_password)
