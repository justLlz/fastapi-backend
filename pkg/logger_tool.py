import logging
import os
import sys
from pathlib import Path

import loguru

from pkg import BASE_DIR, SYS_ENV


class LogConfig:
    """日志配置中心"""
    LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DIR: Path = BASE_DIR / "logs"
    FILE_NAME: str = "app_{time:YYYY-MM-DD}.log"
    ROTATION: str = os.getenv("LOG_ROTATION", "00:00")  # 支持大小/时间轮转
    RETENTION: str = os.getenv("LOG_RETENTION", "30 days")
    COMPRESSION: str = "zip"  # 压缩格式


class LogFormat:
    """日志格式模板"""
    CONSOLE = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <magenta>{extra[trace_id]}</magenta> - <level>{message}</level>"

    FILE = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {extra[trace_id]} - {message}"


def remove_logging_logger():
    # 清除uvicorn相关日志记录器的默认处理日志处理器
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
    logging.getLogger("uvicorn").handlers = []
    pass


def init_logger(env: str = "local"):
    loguru_logger = loguru.logger
    loguru_logger.info("Init logger...")

    try:
        LogConfig.DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        loguru_logger.error(f"Failed to create log directory: {e}")
        sys.exit(1)

    loguru_logger.remove()
    loguru_logger.configure(extra={"trace_id": "-"})

    if env in ("local", "local_test"):
        loguru_logger.add(
            sink=sys.stderr,
            format=LogFormat.CONSOLE,
            level=LogConfig.LEVEL,
            enqueue=True,
            colorize=True,
            diagnose=True
        )
    else:
        loguru_logger.add(
            sink=LogConfig.DIR / LogConfig.FILE_NAME,
            format=LogFormat.FILE,
            level=LogConfig.LEVEL,
            rotation=LogConfig.ROTATION,
            retention=LogConfig.RETENTION,
            compression=LogConfig.COMPRESSION,
            diagnose=True,
            enqueue=True
        )

    loguru_logger.info("Init logger successfully.")
    return loguru_logger


logger = init_logger(SYS_ENV)
