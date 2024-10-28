import sys
import time
from logging import INFO
from pathlib import Path

from loguru import logger

# 定义日志路径和格式
LOG_DIRECTORY: Path = Path(__file__).parent.parent / 'logs'
LOG_FILE_PATH: Path = LOG_DIRECTORY.joinpath(f"{time.strftime('%Y-%m-%d')}_error.log")
LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss ZZ}|{level}|{file}:{line} in {function}|{extra[trace_id]}| {message}"


def setup_logger(log_file_path: Path = LOG_FILE_PATH, log_level: int = INFO) -> None:
    """设置日志记录器的配置"""
    try:
        # 创建日志目录（如果不存在）
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create log directory: {e}")
        sys.exit(1)

    # 文件日志配置
    logger.add(
        sink=log_file_path,
        format=LOG_FORMAT,
        level=log_level,
        rotation="12:00",  # 每天中午12点轮转
        retention="5 days",  # 保留5天的日志
        enqueue=True
    )


# 初始化日志配置
setup_logger()

__all__ = ["logger"]
