from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from pkg.logger_tool import logger


class ApsSchedulerTool:
    """一个简单稳妥的 AsyncIO APScheduler 封装。

    特性：
    - 统一 start()/shutdown()，可重复调用且幂等
    - 提供 add_cron_job() 语法糖
    - 新增 register_* 系列：先登记、后启动；也支持已启动后即时添加
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

        # 用于在 start() 前登记任务（存放“调用 add_job 的参数”）
        # 元素: tuple[func, args(tuple), kwargs(dict)]
        self._pending_jobs: list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = []

    # ------------------------- 基础生命周期 -------------------------
    def start(self) -> None:
        """启动 Scheduler（幂等）。

        提示：`register_func` 已废弃，可直接使用 register_* 系列 API 在 start 前登记任务。
        """
        if self._started:
            logger.debug("Scheduler already started; skip start().")
            return

        # 在真正 start() 之前，把 pending 的任务一次性灌入调度器
        for func, args, kwargs in self._pending_jobs:
            job = self._scheduler.add_job(func, *args, **kwargs)
            logger.info(f"[startup] Added job: id={job.id}, trigger={job.trigger}")

        # 清空待注册队列
        self._pending_jobs.clear()

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

    # ------------------------- 新增：先登记、后启动 -------------------------
    def _ensure_default_job_options(self, kwargs: dict[str, Any]) -> None:
        # 统一填充默认 max_instances（单个 job 可覆盖）
        kwargs.setdefault("max_instances", self._default_max_instances)

    def register_job(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """登记一个任务。未启动时存入队列，启动后一次性添加；若已启动则立即添加。

        用法与 `scheduler.add_job` 等价：
            register_job(my_func, 'interval', seconds=5, id='foo')
            register_job(my_func, 'trigger', minutes=30)
            register_job(my_func, 'date', run_date=datetime(...))
        """
        self._ensure_default_job_options(kwargs)
        job_id = kwargs.get("id", func.__name__)

        if self._started:
            job = self._scheduler.add_job(func, *args, **kwargs)
            logger.info(f"Added job: id={job.id}, trigger={job.trigger}")
        else:
            self._pending_jobs.append((func, args, kwargs))

        return job_id

    def register_cron_job(
            self,
            func: Callable[..., Any],
            *,
            job_id: str | None = None,
            replace_existing: bool = True,
            cron_kwargs: dict[str, Any],
            **job_options: Any,
    ) -> str:
        """登记一个 Cron 任务。"""
        if not cron_kwargs:
            raise ValueError("cron_kwargs cannot be empty")
        trigger = CronTrigger(**cron_kwargs)
        return self.register_job(
            func,
            trigger=trigger,
            id=(job_id or func.__name__),
            replace_existing=replace_existing,
            **job_options,
        )

    def register_interval_job(
            self,
            func: Callable[..., Any],
            *,
            job_id: str | None = None,
            replace_existing: bool = True,
            interval_kwargs: dict[str, Any],
            **job_options: Any,
    ) -> str:
        """登记一个 Interval 任务。"""
        if not interval_kwargs:
            raise ValueError("interval_kwargs cannot be empty")
        trigger = IntervalTrigger(**interval_kwargs)
        return self.register_job(
            func,
            trigger=trigger,
            id=(job_id or func.__name__),
            replace_existing=replace_existing,
            **job_options,
        )

    def register_date_job(
            self,
            func: Callable[..., Any],
            *,
            job_id: str | None = None,
            replace_existing: bool = True,
            date_kwargs: dict[str, Any],
            **job_options: Any,
    ) -> str:
        """登记一个 Date 一次性任务。"""
        if not date_kwargs:
            raise ValueError("date_kwargs cannot be empty")
        trigger = DateTrigger(**date_kwargs)
        return self.register_job(
            func,
            trigger=trigger,
            id=(job_id or func.__name__),
            replace_existing=replace_existing,
            **job_options,
        )

    # ------------------------- 查询/控制 -------------------------
    @property
    def scheduler(self) -> AsyncIOScheduler:
        return self._scheduler

    def get_job(self, job_id: str):
        return self._scheduler.get_job(job_id)

    def remove_job(self, job_id: str) -> None:
        self._scheduler.remove_job(job_id)
        logger.info(f"Removed job: id={job_id}")

    def pause_job(self, job_id: str) -> None:
        self._scheduler.pause_job(job_id)
        logger.info(f"Paused job: id={job_id}")

    def resume_job(self, job_id: str) -> None:
        self._scheduler.resume_job(job_id)
        logger.info(f"Resumed job: id={job_id}")

    def running(self) -> bool:
        return self._started


def new_aps_scheduler_tool(
        timezone: str, job_defaults: dict[str, Any] | None = None, max_instances: int = 50
) -> ApsSchedulerTool:
    return ApsSchedulerTool(timezone=timezone, job_defaults=job_defaults, max_instances=max_instances)
