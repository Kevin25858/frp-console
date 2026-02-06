"""
日志工具模块
提供彩色终端日志输出功能
"""
from datetime import datetime
from typing import Dict, Tuple


class ColorLogger:
    """终端彩色日志输出工具类"""

    # ANSI 颜色代码
    COLORS: Dict[str, str] = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bg_red': '\033[41m',
        'bg_green': '\033[42m',
        'bg_yellow': '\033[43m',
        'bg_blue': '\033[44m',
    }

    # 日志级别配置（颜色和图标）
    LEVELS: Dict[str, Tuple[str, str]] = {
        'DEBUG': ('dim', '◼'),
        'INFO': ('cyan', 'ℹ'),
        'SUCCESS': ('green', '✓'),
        'WARNING': ('yellow', '⚠'),
        'ERROR': ('red', '✗'),
        'CRITICAL': ('bg_red', '🔥'),
    }

    @classmethod
    def log(cls, level: str, message: str, prefix: str = '') -> None:
        """
        输出带颜色的日志

        Args:
            level: 日志级别 (DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
            message: 日志消息
            prefix: 可选的前缀标签
        """
        color_name, icon = cls.LEVELS.get(level, ('white', '•'))
        color = cls.COLORS.get(color_name, '')
        reset = cls.COLORS['reset']
        timestamp = datetime.now().strftime('%H:%M:%S')

        # 构建前缀
        prefix_str = f"[{cls.COLORS['dim']}{prefix}{reset}] " if prefix else ""

        # 输出格式: [时间] [图标] [前缀] 消息
        log_line = f"{cls.COLORS['dim']}[{timestamp}]{reset} {color}{icon}{reset} {prefix_str}{message}"
        print(log_line)

    @classmethod
    def debug(cls, message: str, prefix: str = '') -> None:
        """输出 DEBUG 级别日志"""
        cls.log('DEBUG', message, prefix)

    @classmethod
    def info(cls, message: str, prefix: str = '') -> None:
        """输出 INFO 级别日志"""
        cls.log('INFO', message, prefix)

    @classmethod
    def success(cls, message: str, prefix: str = '') -> None:
        """输出 SUCCESS 级别日志"""
        cls.log('SUCCESS', message, prefix)

    @classmethod
    def warning(cls, message: str, prefix: str = '') -> None:
        """输出 WARNING 级别日志"""
        cls.log('WARNING', message, prefix)

    @classmethod
    def error(cls, message: str, prefix: str = '') -> None:
        """输出 ERROR 级别日志"""
        cls.log('ERROR', message, prefix)

    @classmethod
    def critical(cls, message: str, prefix: str = '') -> None:
        """输出 CRITICAL 级别日志"""
        cls.log('CRITICAL', message, prefix)


class AnsiToHtml:
    """将 ANSI 颜色代码转换为 HTML"""

    # ANSI 代码到 CSS 样式的映射
    STYLE_MAP: Dict[str, str] = {
        '0': 'reset', '1': 'bold', '2': 'dim',
        '30': 'color:#000', '31': 'color:#ff6b6b', '32': 'color:#51cf66',
        '33': 'color:#ffd43b', '34': 'color:#4dabf7', '35': 'color:#e599f7',
        '36': 'color:#22b8cf', '37': 'color:#f8f9fa',
        '90': 'color:#666', '91': 'color:#ff6b6b', '92': 'color:#51cf66',
        '93': 'color:#ffd43b', '94': 'color:#4dabf7', '95': 'color:#e599f7',
        '96': 'color:#22b8cf', '97': 'color:#fff',
        '40': 'bg:#000', '41': 'bg:#ff6b6b', '42': 'bg:#51cf66',
        '43': 'bg:#ffd43b', '44': 'bg:#4dabf7', '45': 'bg:#e599f7',
        '46': 'bg:#22b8cf', '47': 'bg:#f8f9fa',
    }

    # ANSI 颜色代码正则表达式
    ANSI_PATTERN = None  # 将在类加载时初始化

    @classmethod
    def convert(cls, text: str) -> str:
        """
        将 ANSI 文本转换为 HTML

        Args:
            text: 包含 ANSI 颜色代码的文本

        Returns:
            转换后的 HTML 文本
        """
        if not text:
            return ''

        import re

        if cls.ANSI_PATTERN is None:
            cls.ANSI_PATTERN = re.compile(r'\x1b\[(\d+;?)*m')

        result = []
        current_style = []
        last_end = 0

        for match in cls.ANSI_PATTERN.finditer(text):
            # 添加匹配前的文本
            if match.start() > last_end:
                content = text[last_end:match.start()]
                if content:
                    if current_style:
                        style = ';'.join(current_style)
                        result.append(f'<span style="{style}">{content}</span>')
                    else:
                        result.append(content)

            # 解析 ANSI 代码
            codes = match.group(0)[2:-1].split(';')
            for code in codes:
                if code == '0':
                    current_style = []
                elif code in ['1', '2']:
                    if code == '1':
                        current_style.append('font-weight:bold')
                    else:
                        current_style.append('opacity:0.7')
                elif code in cls.STYLE_MAP:
                    style = cls.STYLE_MAP[code]
                    if style.startswith('color:'):
                        current_style.append(style)
                    elif style.startswith('bg:'):
                        current_style.append(f'background-color:{style[3:]}')

            last_end = match.end()

        # 添加剩余文本
        if last_end < len(text):
            content = text[last_end:]
            if current_style:
                style = ';'.join(current_style)
                result.append(f'<span style="{style}">{content}</span>')
            else:
                result.append(content)

        return ''.join(result)