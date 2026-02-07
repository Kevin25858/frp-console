"""
配置服务模块
处理 frpc 配置的验证和导出
"""
import os
from datetime import datetime
from typing import Tuple, Optional

from config import Config
from utils.logger import ColorLogger


class ConfigService:
    """配置服务类 - 仅用于配置验证和导出"""

    @staticmethod
    def get_client_log_path(client_id: int) -> str:
        """
        获取客户端日志文件路径

        Args:
            client_id: 客户端 ID

        Returns:
            日志文件路径
        """
        return f"{Config.LOGS_DIR}/client-{client_id}.log"
