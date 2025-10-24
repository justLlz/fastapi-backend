# internal/celery_tasks/bootstrap_db.py
import asyncio
import os

from celery import signals

from internal.infra.celery_db import close_async_celery_db, init_async_celery_db
from pkg.logger_helper import logger


@signals.worker_process_init.connect
def _init_db_in_worker_process_init(**_):
    # 子进程里初始化，避免在 fork 前创建资源
    init_async_celery_db()
    logger.info(f"[init] worker_process_init ok (pid={os.getpid()})")

@signals.worker_process_shutdown.connect
def _close_db_in_worker_process_shutdown(**_):
    # Celery 信号处理器是同步函数，这里直接跑一个短暂 event loop 最稳
    asyncio.run(close_async_celery_db())
    logger.info(f"[close] worker_process_shutdown ok (pid={os.getpid()})")