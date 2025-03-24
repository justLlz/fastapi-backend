import sys
import time
from pathlib import Path

import loguru

from pkg import colorprint


def init_logger(log_level: int = "INFO"):
    # 定义日志路径和格式
    log_directory: Path = Path().cwd() / 'logs'
    log_file_path: Path = log_directory.joinpath(f"{time.strftime('%Y-%m-%d')}_error.log")
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss ZZ}|{level}|{name}:{line}|{extra[trace_id]}: {message}"

    colorprint.green("Init logger...")
    """设置日志记录器的配置"""
    try:
        # 创建日志目录（如果不存在）
        log_directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        colorprint.red(f"Failed to create log directory: {e}")
        sys.exit(1)

    l = loguru.logger
    l = l.patch(lambda record: record["extra"].setdefault("trace_id", "-"))
    # 添加文件日志处理器
    l.add(
        sink=log_file_path,
        format=log_format,
        level=log_level,
        rotation="12:00",  # 每天中午12点轮转
        retention="7 days",  # 保留7天的日志
        enqueue=True
    )
    colorprint.green("Init logger successfully.")
    return l


Logger = init_logger()
