from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from pkg.logger_tool import logger


class ApsSchedulerTool:
    """一个简单稳妥的 AsyncIO APScheduler 封装。

    特性：
    - 统一 start()/shutdown()，可重复调用且幂等
    - 提供 add_cron_job() 语法糖
    - 支持在 FastAPI lifespan / CLI 里以 async 上下文管理器使用
    - 允许按需暴露底层 scheduler
    """

    def __init__(
            self,
            *,
            timezone: str = "UTC",
            job_defaults: dict[str, Any] | None = None,
            max_instances: int = 50,
    ) -> None:
        self._scheduler = AsyncIOScheduler(timezone=timezone, job_defaults=job_defaults or {})
        # 给所有 job 一个默认的 max_instances；单个 job 可覆盖
        self._default_max_instances = max_instances
        self._started: bool = False

    # ------------------------- 基础生命周期 -------------------------
    def start(self) -> None:
        """启动 Scheduler（幂等）。"""
        if self._started:
            logger.debug("Scheduler already started; skip start().")
            return
        logger.info("Starting scheduler…")
        try:
            self._scheduler.start()
            self._started = True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Scheduler startup error: {e}")
            raise
        logger.info("Scheduler started successfully")

    async def shutdown(self, *, wait: bool = True) -> None:
        """关闭 Scheduler（幂等）。"""
        if not self._started:
            logger.debug("Scheduler not started; skip shutdown().")
            return
        logger.info("Stopping scheduler…")
        try:
            self._scheduler.shutdown(wait=wait)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Scheduler shutdown error: {e}")
            raise
        else:
            logger.info("Scheduler stopped gracefully")
        finally:
            self._started = False

    # ------------------------- 便捷添加任务 -------------------------
    def add_cron_job(
            self,
            func: Callable[..., Any],
            *,
            job_id: str | None = None,
            max_instances: int | None = None,
            replace_existing: bool = True,
            **cron_kwargs: Any,
    ) -> str:
        """以 Cron 方式添加任务。

        示例：
            tool.add_cron_job(handle_deploy_svc_monitor, minute='*', second=0)
        """
        trigger = CronTrigger(**cron_kwargs)
        job = self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            max_instances=max_instances or self._default_max_instances,
            replace_existing=replace_existing,
        )
        logger.info(
            "Added cron job: id=%s, trigger=%s, max_instances=%s",
            job.id,
            trigger,
            job.max_instances,
        )
        return job.id

    def add_job(self, *args: Any, **kwargs: Any):
        """透传底层 add_job，以便使用除 Cron 外的触发器（interval/date 等）。"""
        if "max_instances" not in kwargs:
            kwargs["max_instances"] = self._default_max_instances
        job = self._scheduler.add_job(*args, **kwargs)
        logger.info("Added job: id=%s, trigger=%s", job.id, job.trigger)
        return job

    # ------------------------- 查询/控制 -------------------------
    @property
    def scheduler(self) -> AsyncIOScheduler:
        return self._scheduler

    def get_job(self, job_id: str):
        return self._scheduler.get_job(job_id)

    def remove_job(self, job_id: str) -> None:
        self._scheduler.remove_job(job_id)
        logger.info("Removed job: id=%s", job_id)

    def pause_job(self, job_id: str) -> None:
        self._scheduler.pause_job(job_id)
        logger.info("Paused job: id=%s", job_id)

    def resume_job(self, job_id: str) -> None:
        self._scheduler.resume_job(job_id)
        logger.info("Resumed job: id=%s", job_id)

    def running(self) -> bool:
        return self._started


apscheduler_manager = ApsSchedulerTool(timezone="UTC", max_instances=50)

