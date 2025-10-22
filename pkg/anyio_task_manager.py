from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import Any

import anyio
from anyio import CancelScope, CapacityLimiter, create_task_group, fail_after
from anyio.abc import TaskGroup

from pkg.logger_helper import logger


@dataclass
class TaskInfo:
    task_id: str
    name: str
    scope: CancelScope
    status: str = "running"  # running | completed | failed | cancelled | timeout
    result: Any = None
    exception: BaseException | None = None


class AnyioTaskManager:
    def __init__(self, max_tasks: int = 10):
        self.max_tasks = max_tasks
        self._limiter = CapacityLimiter(max_tasks)
        self._tg: TaskGroup | None = None
        self._tg_started = False
        self._lock = anyio.Lock()
        self.tasks: dict[str, TaskInfo] = {}

    # ---------- lifecycle ----------
    async def start(self):
        if self._tg_started:
            return
        self._tg = await create_task_group().__aenter__()  # 持久 TaskGroup
        self._tg_started = True
        logger.info("AsyncTaskManagerAnyIO started.")

    async def shutdown(self):
        logger.info("Shutting down AsyncTaskManagerAnyIO...")
        async with self._lock:
            for info in self.tasks.values():
                try:
                    info.scope.cancel()
                except Exception as e:
                    logger.warning(f"Error canceling task: {e}")
        if self._tg_started and self._tg is not None:
            try:
                await self._tg.__aexit__(None, None, None)
            finally:
                self._tg = None
                self._tg_started = False
        logger.info("AsyncTaskManagerAnyIO stopped.")

    # ---------- helpers ----------
    @staticmethod
    def get_coro_func_name(coro_func: Callable[..., Awaitable[Any]]) -> str:
        if getattr(coro_func, "__name__", None) == "<lambda>":
            raise ValueError("Lambda functions are not supported for task tracking!")
        if hasattr(coro_func, "__self__"):
            return f"{coro_func.__self__.__class__.__name__}.{coro_func.__name__}"
        return coro_func.__name__

    async def _run_task_inner(
            self,
            info: TaskInfo,
            coro_func: Callable[..., Awaitable[Any]],
            args_tuple: tuple,
            kwargs_dict: dict,
            timeout: float | None,
    ):
        coro_name = info.name
        task_id = info.task_id

        try:
            async with self._limiter:
                logger.info(f"Task {coro_name} {task_id} started.")

                if timeout and timeout > 0:
                    with fail_after(timeout):
                        result = await coro_func(*args_tuple, **kwargs_dict)
                else:
                    result = await coro_func(*args_tuple, **kwargs_dict)

                info.status = "completed"
                info.result = result
                logger.info(f"Task {coro_name} {task_id} completed.")

        except TimeoutError as te:
            info.status = "timeout"
            info.exception = te
            logger.error(f"Task {coro_name} {task_id} timed out after {timeout} seconds.")
        except BaseException as e:
            if isinstance(e, anyio.get_cancelled_exc_class()):
                info.status = "cancelled"
                logger.info(f"Task {coro_name} {task_id} cancelled.")
            else:
                info.status = "failed"
                info.exception = e
                logger.error(f"Task {coro_name} {task_id} failed, err={e}")
        finally:
            async with self._lock:
                self.tasks.pop(task_id, None)

    # ---------- public APIs ----------
    async def add_task(
            self,
            task_id: str | int,
            *,
            coro_func: Callable[..., Awaitable[Any]],
            args_tuple: tuple = (),
            kwargs_dict: dict | None = None,
            timeout: float | None = None,
    ) -> bool:
        """仅进程内去重；多 worker 环境下可能重复提交。"""
        if not self._tg_started or self._tg is None:
            raise RuntimeError("AsyncTaskManagerAnyIO is not started. Call await start() first.")

        if isinstance(task_id, int):
            task_id = str(task_id)

        kwargs_dict = kwargs_dict or {}
        coro_name = self.get_coro_func_name(coro_func)

        async with self._lock:
            if task_id in self.tasks:
                logger.warning(f"Task {task_id} already exists (same process).")
                return False

            scope = CancelScope()
            info = TaskInfo(task_id=task_id, name=coro_name, scope=scope)
            self.tasks[task_id] = info
            self._tg.start_soon(self._run_task_inner, info, coro_func, args_tuple, kwargs_dict, timeout)
        return True

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            info = self.tasks.get(task_id)
            if info:
                info.scope.cancel()
                logger.info(f"Task {task_id} cancelled.")
                return True
            logger.warning(f"Task {task_id} not found.")
            return False

    async def get_task_status(self) -> dict[str, bool]:
        async with self._lock:
            return {tid: (ti.status == "running") for tid, ti in self.tasks.items()}

    async def run_gather_with_concurrency(
            self,
            coro_func: Callable[..., Awaitable[Any]],
            args_tuple_list: list[tuple],
            timeout: float | None = None,
    ) -> list[Any]:
        """
        并发执行多个相同函数的不同参数，并支持整体超时控制

        Args:
            coro_func: 异步函数
            args_tuple_list: 参数元组列表
            timeout: 整体超时时间（秒）

        Returns:
            list[Any]: 结果列表，成功为结果值，失败为异常对象
        """
        coro_name = self.get_coro_func_name(coro_func)
        results: list[Any] = [None] * len(args_tuple_list)

        async def _wrapped(index: int, args: tuple):
            async with self._limiter:
                try:
                    logger.info(f"Task-{index} ({coro_name}, {args}) started.")

                    # 单个任务的超时控制
                    if timeout and timeout > 0:
                        with fail_after(timeout):
                            res = await coro_func(*args)
                    else:
                        res = await coro_func(*args)

                    results[index] = res
                    logger.info(f"Task-{index} ({coro_name}, {args}) completed.")
                except TimeoutError:
                    results[index] = None
                    logger.error(f"Task-{index} ({coro_name}, {args}) timed out after {timeout} seconds.")
                except BaseException as e:
                    results[index] = None
                    logger.error(f"Task-{index} ({coro_name}, {args}) failed. err={e}")

        # 使用任务组管理所有任务
        async with create_task_group() as tg:
            for i, args_tuple in enumerate(args_tuple_list):
                tg.start_soon(_wrapped, i, args_tuple)

        return results

    async def run_in_thread(
            self,
            task_id: str | int,
            coro_func: Callable[..., Any],
            *,
            args_tuple: tuple,
            kwargs: dict | None = None,
            timeout: float | None = None,
            cancellable: bool = False,
    ) -> Any:
        """
        用 AnyIO 线程池执行同步函数（不会阻塞事件循环）。
        - kwargs：同步函数的关键字参数（to_thread.run_sync 不接受 kwargs，因此用 partial 包装）
        - timeout：超时时间（秒），超时抛 anyio.TimeoutError
        - cancellable：是否允许取消在等待线程结果时生效（默认为 False）
        """
        logger.info(f"Task {task_id} started in a thread.")
        bound = partial(coro_func, *args_tuple, **(kwargs or {}))
        async with self._limiter:
            if timeout and timeout > 0:
                with fail_after(timeout):
                    return await anyio.to_thread.run_sync(bound, cancellable=cancellable)
            return await anyio.to_thread.run_sync(bound, cancellable=cancellable)

    async def run_in_process(
            self,
            task_id: str | int,
            coro_func: Callable[..., Any],
            *,
            args_tuple: tuple,
            kwargs: dict | None = None,
            timeout: float | None = None,
    ) -> Any:
        """
        用 AnyIO 进程池执行同步函数（CPU 密集/需隔离 GIL 的场景）。
        - 注意：func 必须是可 picklable 的顶层函数；args/kwargs 也需可序列化
        - Windows/macOS 默认 spawn，闭包/lambda/本地函数会失败
        - 取消语义：只能在等待结果时取消；真正的子进程中断取决于平台与 anyio 实现
        """
        logger.info(f"Task {task_id} started in process.")
        bound = partial(coro_func, *args_tuple, **(kwargs or {}))
        async with self._limiter:
            if timeout and timeout > 0:
                with fail_after(timeout):
                    return await anyio.to_process.run_sync(bound)
            return await anyio.to_process.run_sync(bound)


# 全局实例（注意：需在 FastAPI 启动时 start，在关闭时 shutdown）
anyio_task_manager = AnyioTaskManager(max_tasks=100)
