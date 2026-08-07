"""
日志工具模块
在终端输出带颜色的日志，方便调试

什么是 ANSI 颜色代码：
    终端（如 Linux 的 bash、Windows Terminal）支持一种特殊的字符序列，
    以 \033[ 开头，能控制文字颜色、背景色、样式等。
    例如 \033[91m 表示后面的文字用红色，\033[0m 表示重置所有样式。

为什么不用 Python 自带的 logging 模块：
    1. logging 配置复杂，对初学者不友好
    2. 本项目是单进程应用，不需要复杂的日志路由
    3. 彩色输出更直观，便于在终端里区分日志级别
    4. 生产环境如果要持久化日志，可以重定向 stdout 到文件
"""
from datetime import datetime


# ANSI 颜色代码（终端控制字符）
RESET = '\033[0m'      # 重置颜色
DIM = '\033[2m'        # 暗淡
RED = '\033[91m'       # 红色
GREEN = '\033[92m'     # 绿色
YELLOW = '\033[93m'    # 黄色
CYAN = '\033[96m'      # 青色


class ColorLogger:
    """终端彩色日志输出工具类"""

    # 所有方法都是 classmethod，不需要实例化就能用
    # 直接 ColorLogger.info('xxx') 调用，比 logger = Logger(); logger.info() 简洁

    @classmethod
    def log(cls, level, message, prefix=''):
        """
        输出一条日志

        参数:
            level:   日志级别，比如 'INFO'、'ERROR'
            message: 要输出的内容
            prefix:  可选的标签，比如 'Auth'、'Client'
        """
        # 根据级别选择颜色和文字标签
        # 不同级别用不同颜色，方便一眼区分重要程度
        if level == 'DEBUG':
            color = DIM
            tag = 'DEBUG'
        elif level == 'INFO':
            color = CYAN
            tag = 'INFO'
        elif level == 'SUCCESS':
            color = GREEN
            tag = 'OK'
        elif level == 'WARNING':
            color = YELLOW
            tag = 'WARN'
        elif level == 'ERROR':
            color = RED
            tag = 'ERROR'
        else:
            color = ''
            tag = level

        # 获取当前时间，只取时分秒
        # 不取日期是因为日志通常实时看，日期太占地方
        now = datetime.now()
        time_str = now.strftime('%H:%M:%S')

        # 拼接前缀标签
        # prefix 是模块标签，比如 [Auth]、[Database]，用暗淡颜色不抢眼
        if prefix:
            prefix_str = '[' + DIM + prefix + RESET + '] '
        else:
            prefix_str = ''

        # 拼接完整日志行并输出
        # 格式：[12:34:56] [INFO] [Auth] 用户 admin 登录成功
        # 时间用暗淡，级别用对应颜色，内容默认色
        log_line = DIM + '[' + time_str + ']' + RESET + ' ' + color + '[' + tag + ']' + RESET + ' ' + prefix_str + message
        print(log_line)

    @classmethod
    def debug(cls, message, prefix=''):
        """输出 DEBUG 级别日志（最详细，通常只在开发时用）"""
        cls.log('DEBUG', message, prefix)

    @classmethod
    def info(cls, message, prefix=''):
        """输出 INFO 级别日志（一般信息，比如启动成功）"""
        cls.log('INFO', message, prefix)

    @classmethod
    def success(cls, message, prefix=''):
        """输出 SUCCESS 级别日志（操作成功，比如客户端启动）"""
        cls.log('SUCCESS', message, prefix)

    @classmethod
    def warning(cls, message, prefix=''):
        """输出 WARNING 级别日志（警告，不影响运行但要注意）"""
        cls.log('WARNING', message, prefix)

    @classmethod
    def error(cls, message, prefix=''):
        """输出 ERROR 级别日志（错误，操作失败了）"""
        cls.log('ERROR', message, prefix)

    @classmethod
    def critical(cls, message, prefix=''):
        """输出 CRITICAL 级别日志（严重错误，系统可能无法继续运行）"""
        cls.log('CRITICAL', message, prefix)
