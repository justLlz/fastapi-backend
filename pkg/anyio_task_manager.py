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

        # 处理 partial 对象
        if isinstance(coro_func, partial):
            func = coro_func.func
            if hasattr(func, "__self__"):
                return f"{func.__self__.__class__.__name__}.{func.__name__}"
            elif hasattr(func, "__name__"):
                return func.__name__
            else:
                return "partial"

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
            sync_func: Callable[..., Any],
            *,
            task_id: str | int = None,
            args_tuple: tuple | None = None,
            kwargs_dict: dict | None = None,
            timeout: float | None = None,
            cancellable: bool = False
    ) -> Any:
        """
        用 AnyIO 线程池执行同步函数（不会阻塞事件循环）。
        - kwargs：同步函数的关键字参数（to_thread.run_sync 不接受 kwargs，因此用 partial 包装）
        - timeout：超时时间（秒），超时抛 anyio.TimeoutError
        - cancellable：是否允许取消在等待线程结果时生效（默认为 False）
        """
        func_name = self.get_coro_func_name(sync_func)
        logger.info(f"Task {func_name} started in a thread.")
        bound = partial(sync_func, *(args_tuple or ()), **(kwargs_dict or {}))
        async with self._limiter:
            if timeout and timeout > 0:
                with fail_after(timeout):
                    return await anyio.to_thread.run_sync(bound, cancellable=cancellable)
            return await anyio.to_thread.run_sync(bound, cancellable=cancellable)

    async def run_in_process(
            self,
            sync_func: Callable[..., Any],
            *,
            args_tuple: tuple | None = None,
            kwargs_dict: dict | None = None,
            timeout: float | None = None,
    ) -> Any:
        """
        用 AnyIO 进程池执行同步函数（CPU 密集/需隔离 GIL 的场景）。
        - 注意：func 必须是可 picklable 的顶层函数；args/kwargs 也需可序列化
        - Windows/macOS 默认 spawn，闭包/lambda/本地函数会失败
        - 取消语义：只能在等待结果时取消；真正的子进程中断取决于平台与 anyio 实现
        """
        func_name = self.get_coro_func_name(sync_func)
        logger.info(f"Task {func_name} started in process.")
        bound = partial(sync_func, *(args_tuple or ()), **(kwargs_dict or {}))
        async with self._limiter:
            if timeout and timeout > 0:
                with fail_after(timeout):
                    return await anyio.to_process.run_sync(bound)
            return await anyio.to_process.run_sync(bound)

    async def run_in_threads(
            self,
            sync_func: Callable[..., Any],
            *,
            args_tuple_list: list[tuple] | None = None,
            kwargs_dict_list: list[dict] | None = None,
            timeout: float | None = None,
            cancellable: bool = False,
    ) -> list[Any]:
        """
        使用 AnyIO 线程池并发执行一批 *同步* 函数调用（不会阻塞事件循环）。

        Args:
            sync_func: 同步函数（I/O 密集或会释放 GIL 的计算可用）
            args_tuple_list: 参数元组列表，对应每个任务的位置参数
            kwargs_dict_list: 关键字参数的字典列表（可为 None；若提供，长度应与 args_tuple_list 相同）
            timeout: 单个任务的超时（秒）；超时则该任务返回 None，并记录日志
            cancellable: 等待线程结果时是否可取消（传给 anyio.to_thread.run_sync）

        Returns:
            list[Any]: 与输入顺序一一对应的结果列表；失败/超时为 None
        """
        args_tuple_list, kwargs_dict_list = self._check_rebuild_args_kwargs(args_tuple_list, kwargs_dict_list)

        results: list[Any] = [None] * len(args_tuple_list)
        func_name = self.get_coro_func_name(sync_func)

        async def _one(index: int, args_tuple: tuple, kwargs_dict: dict | None):
            bound = partial(sync_func, *(args_tuple or ()), **(kwargs_dict or {}))
            async with self._limiter:
                try:
                    logger.info(f"ThreadTask-{index} ({func_name}, args={args_tuple}, kwargs={kwargs_dict}) started.")
                    if timeout and timeout > 0:
                        with fail_after(timeout):
                            res = await anyio.to_thread.run_sync(bound, cancellable=cancellable)
                    else:
                        res = await anyio.to_thread.run_sync(bound, cancellable=cancellable)
                    results[index] = res
                    logger.info(f"ThreadTask-{index} ({func_name}) completed.")
                except TimeoutError:
                    results[index] = None
                    logger.error(f"ThreadTask-{index} ({func_name}) timed out after {timeout} seconds.")
                except BaseException as e:
                    # 取消语义：仅在等待结果时能被取消；底层线程不会被强杀
                    if isinstance(e, anyio.get_cancelled_exc_class()):
                        logger.info(f"ThreadTask-{index} ({func_name}) cancelled while awaiting result.")
                    else:
                        logger.error(f"ThreadTask-{index} ({func_name}) failed. err={e}")
                    results[index] = None

        async with create_task_group() as tg:
            for i, (args, kwargs) in enumerate(zip(args_tuple_list, kwargs_dict_list, strict=False)):
                tg.start_soon(_one, i, args, kwargs)

        return results

    async def run_in_processes(
            self,
            sync_func: Callable[..., Any],
            args_tuple_list: list[tuple] | None = None,
            kwargs_dict_list: list[dict] | None = None,
            *,
            timeout: float | None = None,
    ) -> list[Any]:
        """
        使用 AnyIO 进程池并发执行一批 *同步* 函数调用（适合 CPU 密集或需绕开 GIL 的场景）。

        注意：
        - func 必须是顶层可 picklable 的函数；args/kwargs 也需可序列化
        - Windows / macOS 默认 spawn，闭包、lambda、本地函数会失败
        - 取消语义：只能在等待结果阶段取消；子进程不会被“强杀”，需在 func 内部自管超时/分段返回

        Args:
            sync_func: 同步函数（顶层可 picklable）
            args_tuple_list: 每个任务的位置参数元组列表
            kwargs_dict_list: 对应的 kwargs 字典列表（可为 None；若提供需与 args_tuple_list 等长）
            timeout: 单个任务的超时时间（秒）；超时该任务返回 None 并记录日志

        Returns:
            list[Any]: 与输入顺序对应的结果列表；失败/超时为 None
        """
        args_tuple_list, kwargs_dict_list = self._check_rebuild_args_kwargs(args_tuple_list, kwargs_dict_list)

        results: list[Any] = [None] * len(args_tuple_list)
        func_name = self.get_coro_func_name(sync_func)

        async def _one(index: int, args_tuple: tuple, kwargs_dict: dict | None):
            # 注意：partial 会被序列化到子进程执行
            bound = partial(sync_func, *(args_tuple or ()), **(kwargs_dict or {}))
            async with self._limiter:
                try:
                    logger.info(f"ProcessTask-{index} ({func_name}, args={args_tuple}, kwargs={kwargs_dict}) started.")
                    if timeout and timeout > 0:
                        with fail_after(timeout):
                            res = await anyio.to_process.run_sync(bound)
                    else:
                        res = await anyio.to_process.run_sync(bound)
                    results[index] = res
                    logger.info(f"ProcessTask-{index} ({func_name}) completed.")
                except TimeoutError:
                    results[index] = None
                    logger.error(f"ProcessTask-{index} ({func_name}) timed out after {timeout} seconds.")
                except BaseException as e:
                    # 等待结果阶段的取消会在这里表现为 CancelledError
                    if isinstance(e, anyio.get_cancelled_exc_class()):
                        logger.info(f"ProcessTask-{index} ({func_name}) cancelled while awaiting result.")
                    else:
                        logger.error(f"ProcessTask-{index} ({func_name}) failed. err={e}")
                    results[index] = None

        async with create_task_group() as tg:
            for i, (args, kwargs) in enumerate(zip(args_tuple_list, kwargs_dict_list, strict=False)):
                tg.start_soon(_one, i, args, kwargs)

        return results

    @staticmethod
    def _check_rebuild_args_kwargs(args_tuple_list: list[tuple], kwargs_dict_list: list[dict] | None):
        args_tuple_list = args_tuple_list or []
        kwargs_dict_list = kwargs_dict_list or [None] * len(args_tuple_list)

        if len(kwargs_dict_list) != len(args_tuple_list):
            raise ValueError("args_tuple_list must be the same length as kwargs_dict_list.")
        return args_tuple_list, kwargs_dict_list


# 全局实例（注意：需在 FastAPI 启动时 start，在关闭时 shutdown）
anyio_task_manager = AnyioTaskManager(max_tasks=100)
