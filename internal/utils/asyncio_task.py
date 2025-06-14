import asyncio
from typing import Any, Awaitable, Callable, Dict

from loguru import logger

from internal.utils.cache_helpers import cache


class AsyncTaskManager:
    def __init__(self, max_tasks: int = 10):
        """初始化任务管理器，设置最大并发任务数"""
        self.tasks: Dict[str, asyncio.Task] = {}  # 任务存储字典
        self.semaphore = asyncio.Semaphore(max_tasks)  # 控制并发数
        self.lock = asyncio.Lock()

    @staticmethod
    def _get_coro_func_name(coro_func: Callable[..., Awaitable[Any]]) -> str:
        # 处理函数名
        if coro_func.__name__ == "<lambda>":
            raise ValueError("Lambda functions are not supported for task tracking!")

        # 如果是类方法，拼接类名
        if hasattr(coro_func, "__self__"):  # 判断是否是绑定方法
            coro_func_name = f"{coro_func.__self__.__class__.__name__}.{coro_func.__name__}"
        else:
            coro_func_name = coro_func.__name__

        return coro_func_name

    async def _run_task(self,
                        task_id: str,
                        coro_func: Callable[..., Awaitable[Any]],
                        timeout: float | None = None,
                        *args,
                        **kwargs):
        coro_func_name = self._get_coro_func_name(coro_func)
        try:
            async with self.semaphore:
                logger.info(f"Task {coro_func_name} {task_id} started.")
                if timeout is not None:
                    try:
                        await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
                    except asyncio.TimeoutError:
                        logger.error(f"Task {coro_func_name} {task_id} timed out after {timeout} seconds.")
                        return
                else:
                    await coro_func(*args, **kwargs)
                    logger.info(f"Task {coro_func_name} {task_id} finished.")
        except asyncio.CancelledError:
            logger.info(f"Task {coro_func_name} {task_id} cancelled.")
        except Exception as e:
            logger.error(f"Task {coro_func_name} {task_id} failed: {e}")
        finally:
            async with self.lock:
                del self.tasks[task_id]

    async def add_task(self,
                       task_id: str,
                       coro_func: Callable[..., Awaitable[Any]],
                       timeout: float | None = None,
                       *args,
                       **kwargs):
        coro_func_name = self._get_coro_func_name(coro_func)
        lock_key = f"lock:{coro_func_name}:{task_id}"
        lock_id = await cache.acquire_lock(lock_key)
        if not lock_id:
            logger.info(f"{coro_func_name}, task_id: {task_id}, acquire_lock fail")
            return False

        handle_result = False  # 统一返回
        try:
            async with self.lock:
                if task_id in self.tasks:
                    logger.warning(f"Task {task_id} already exists.")
                    handle_result = False
                else:
                    try:
                        task = asyncio.create_task(self._run_task(task_id, coro_func, timeout=timeout, *args, **kwargs))
                        self.tasks[task_id] = task
                        handle_result = True
                    except Exception as e:
                        logger.error(f"Create task failed: {e}")
                        handle_result = False
        except Exception as e:
            logger.error(f"Error adding task {coro_func_name} for {task_id}: {e}")
            handle_result = False
        finally:
            try:
                await cache.release_lock(lock_key, lock_id)
            except Exception as e:
                logger.warning(f"release_lock fail: {e}")

        return handle_result

    async def add_task_with_timeout(self, task_id: str, coro_func: Callable[..., Awaitable[Any]], timeout: float, *args,
                                    **kwargs):
        wrapped_coro = asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
        return await self.add_task(task_id, lambda: wrapped_coro)

    async def cancel_task(self, task_id: str):
        """取消指定任务"""
        async with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task.cancel()
                logger.info(f"Task {task_id} cancelled.")
                return True

            logger.warning(f"Task {task_id} not found.")
            return False

    async def get_task_status(self):
        """返回当前任务状态"""
        async with self.lock:
            return {tid: not task.done() for tid, task in self.tasks.items()}

    async def shutdown(self):
        """关闭所有任务"""
        async with self.lock:
            task_list = list(self.tasks.values())
        logger.info(f"Shutting down {len(task_list)} tasks...")

        # 取消所有任务
        for task in task_list:
            task.cancel()

        # 等待所有任务终止
        await asyncio.gather(*task_list, return_exceptions=True)

        async with self.lock:
            self.tasks.clear()
        logger.info("All tasks terminated")


# 创建一个全局任务管理器
async_task_manager = AsyncTaskManager(max_tasks=100)  # 允许最大 5 个并发任务
