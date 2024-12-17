import logging
import sys
import time
from logging import INFO
from pathlib import Path

import loguru

# 定义日志路径和格式
LOG_DIRECTORY: Path = Path().cwd() / 'logs'
LOG_FILE_PATH: Path = LOG_DIRECTORY.joinpath(f"{time.strftime('%Y-%m-%d')}_error.log")
LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss ZZ}|{level}|{name}:{line}|{extra[trace_id]}: {message}"


def init_logger(log_file_path: Path = LOG_FILE_PATH, log_level: int = INFO):
    """设置日志记录器的配置"""
    try:
        # 创建日志目录（如果不存在）
        LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Failed to create log directory: {e}")
        sys.exit(1)

    l = loguru.logger
    l = l.patch(lambda record: record["extra"].setdefault("trace_id", "-"))
    # 添加文件日志处理器
    l.add(
        sink=log_file_path,
        format=LOG_FORMAT,
        level=log_level,
        rotation="12:00",  # 每天中午12点轮转
        retention="7 days",  # 保留7天的日志
        enqueue=True
    )

    return l


logger = init_logger()
print("Init logger successfully.")
