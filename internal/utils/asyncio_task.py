from collections.abc import Awaitable, Callable
from typing import Any
import anyio
from anyio import Semaphore, Lock, TASK_STATUS_IGNORED
from anyio.abc import TaskStatus

from internal.constants import REDIS_KEY_LOCK_PREFIX
from internal.utils.cache_helper import cache
from pkg.logger_helper import logger


class AsyncTaskManager:
    def __init__(self, max_tasks: int = 10):
        self.tasks: dict[str, anyio.abc.CancelScope] = {}
        self.semaphore = Semaphore(max_tasks)
        self.lock = Lock()

    @staticmethod
    def get_coro_func_name(coro_func: Callable[..., Awaitable[Any]]) -> str:
        if coro_func.__name__ == "<lambda>":
            raise ValueError("Lambda functions are not supported for task tracking!")
        if hasattr(coro_func, "__self__"):
            return f"{coro_func.__self__.__class__.__name__}.{coro_func.__name__}"
        return coro_func.__name__

    async def _run_task(
        self,
        task_id: str,
        coro_func: Callable[..., Awaitable[Any]],
        args_tuple: tuple = (),
        kwargs_dict: dict | None = None,
        timeout: float | None = None,
    ) -> None:
        kwargs_dict = kwargs_dict or {}
        coro_func_name = self.get_coro_func_name(coro_func)

        try:
            async with self.semaphore:
                logger.info(f"Task {coro_func_name} {task_id} started.")
                try:
                    if timeout:
                        with anyio.move_on_after(timeout):
                            await coro_func(*args_tuple, **kwargs_dict)
                    else:
                        await coro_func(*args_tuple, **kwargs_dict)
                    logger.info(f"Task {coro_func_name} {task_id} completed.")
                except TimeoutError:
                    logger.error(f"Task {coro_func_name} {task_id} timed out after {timeout} seconds.")
                except Exception as e:
                    logger.error(f"Task {coro_func_name} {task_id} failed, err={e}")
        except anyio.get_cancelled_exc_class():
            logger.info(f"Task {coro_func_name} {task_id} cancelled.")
        finally:
            async with self.lock:
                self.tasks.pop(task_id, None)

    async def run_tasks_return_results(
        self,
        coro_func: Callable[..., Awaitable[Any]],
        args_tuple_list: list[tuple],
    ) -> list[Any]:
        coro_func_name = self.get_coro_func_name(coro_func)

        async def _wrapped(index: int, args_tuple: tuple):
            async with self.semaphore:
                try:
                    logger.info(f"Task-{index} ({coro_func_name}, {args_tuple}) started.")
                    result = await coro_func(*args_tuple)
                    logger.info(f"Task-{index} ({coro_func_name}, {args_tuple}) completed.")
                    return result
                except Exception as e:
                    logger.error(f"Task-{index} ({coro_func_name}, {args_tuple}) failed. err={e}")
                    return None

        async with anyio.create_task_group() as tg:
            results = [await tg.start(_wrapped, i, args_tuple) for i, args_tuple in enumerate(args_tuple_list)]
        return results

    async def add_task(
        self,
        task_id: str,
        *,
        coro_func: Callable[..., Awaitable[Any]],
        args_tuple: tuple = (),
        kwargs_dict: dict | None = None,
        timeout: float | None = None,
    ) -> bool:
        kwargs_dict = kwargs_dict or {}
        coro_func_name = self.get_coro_func_name(coro_func)

        lock_key = f"{REDIS_KEY_LOCK_PREFIX}:{coro_func_name}:{task_id}"
        lock_id = await cache.acquire_lock(lock_key)
        if not lock_id:
            logger.info(f"{coro_func_name}, task_id: {task_id}, acquire_lock fail")
            return False

        try:
            async with self.lock:
                if task_id in self.tasks:
                    logger.warning(f"Task {task_id} already exists.")
                    return False
                # 启动任务并保存 cancel_scope
                async with anyio.create_task_group() as tg:
                    cancel_scope = tg.cancel_scope
                    tg.start_soon(self._run_task, task_id, coro_func, args_tuple, kwargs_dict, timeout)
                    self.tasks[task_id] = cancel_scope
        except Exception as e:
            logger.error(f"Error adding task {coro_func_name} for {task_id}, err={e}")
            return False
        finally:
            await cache.release_lock(lock_key, lock_id)
        return True

    async def cancel_task(self, task_id: str) -> bool:
        async with self.lock:
            cancel_scope = self.tasks.get(task_id)
            if cancel_scope:
                cancel_scope.cancel()
                logger.info(f"Task {task_id} cancelled.")
                return True
            logger.warning(f"Task {task_id} not found.")
            return False

    async def get_task_status(self) -> dict[str, bool]:
        async with self.lock:
            return {tid: not cs.cancel_called for tid, cs in self.tasks.items()}

    async def shutdown(self):
        async with self.lock:
            scopes = list(self.tasks.values())
            self.tasks.clear()

        logger.info(f"Shutting down {len(scopes)} tasks...")
        try:
            for cs in scopes:
                cs.cancel()
            # 等待所有任务退出
            async with anyio.create_task_group() as tg:
                for cs in scopes:
                    tg.start_soon(anyio.sleep, 0)  # dummy to allow cancellation
        except Exception as e:
            logger.error(f"Error shutting down tasks. err={e}")

        logger.info("All tasks terminated")


# 全局实例
async_task_manager = AsyncTaskManager(max_tasks=100)