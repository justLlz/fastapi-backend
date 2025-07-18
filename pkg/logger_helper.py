import logging
import os
import sys
from pathlib import Path

import loguru

from pkg import BASE_DIR, SYS_ENV, colorprint


class LogConfig:
    """日志配置中心"""
    LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DIR: Path = BASE_DIR / "logs"
    FILE_NAME: str = "app_{time:YYYY-MM-DD}.log"
    ROTATION: str = os.getenv("LOG_ROTATION", "00:00 or 100 MB")  # 支持大小/时间轮转
    RETENTION: str = os.getenv("LOG_RETENTION", "30 days")
    COMPRESSION: str = "zip"  # 压缩格式


class LogFormat:
    """日志格式模板"""
    CONSOLE = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | <magenta>{extra[trace_id]}</magenta> - <level>{message}</level>"
    FILE = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {extra[trace_id]} - {message}"


def remove_logging_logger():
    # 清除uvicorn相关日志记录器的默认处理日志处理器
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
    logging.getLogger("uvicorn").handlers = []
    pass


def init_logger(env: str = "dev") -> loguru.logger:
    colorprint.green("Init logger...")
    """设置日志记录器的配置"""
    try:
        LogConfig.DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        colorprint.red(f"Failed to create log directory: {e}")
        raise

    l = loguru.logger
    l.remove()
    l.configure(extra={"trace_id": "-"})

    if env in ("dev", "local"):
        l.add(
            sink=sys.stderr,
            format=LogFormat.CONSOLE,
            level=LogConfig.LEVEL,
            enqueue=True,
            diagnose=True,
            colorize=True
        )
    else:
        l.add(
            sink=LogConfig.DIR / LogConfig.FILE_NAME,
            format=LogFormat.FILE,
            level=LogConfig.LEVEL,
            rotation=LogConfig.ROTATION,
            retention=LogConfig.RETENTION,
            compression=LogConfig.COMPRESSION,
            diagnose=True,
            enqueue=True,

        )
    colorprint.green("Init logger successfully.")
    return l


logger = init_logger(SYS_ENV)
"""
logger.error(f"error message, err: {traceback.format_exc()}")
"""
