import anyio
from collections.abc import Awaitable, Callable
from typing import Any

from anyio.abc import TaskGroup

from pkg.logger_helper import logger


class AsyncTaskManager:
    def __init__(self, max_tasks: int = 10):
        self.tasks: dict[str, TaskGroup] = {}
        self.semaphore = anyio.Semaphore(max_tasks)
        self.lock = anyio.Lock()

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
            timeout: int | None = None,
    ) -> None:
        kwargs_dict = kwargs_dict or {}
        coro_func_name = self.get_coro_func_name(coro_func)
        try:
            async with self.semaphore:
                logger.info(f"Task {coro_func_name} {task_id} started.")
                try:
                    if timeout is not None:
                        with anyio.fail_after(timeout):
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
            timeout: int | None = None,
    ) -> list[Any]:
        """
        并发执行任务并返回结果

        Args:
            coro_func: 异步函数
            args_tuple_list: 参数元组列表
            timeout: 单个任务超时时间

        Returns:
            结果列表，每个元素是结果或异常对象
        """
        coro_func_name = self.get_coro_func_name(coro_func)
        results: list = [None] * len(args_tuple_list)

        async def _wrapped(index: int, args_tuple: tuple):
            async with self.semaphore:
                try:
                    logger.info(f"Task-{index} ({coro_func_name}, {args_tuple}) started.")

                    # 应用超时控制
                    if timeout:
                        with anyio.fail_after(timeout):
                            result = await coro_func(*args_tuple)
                    else:
                        result = await coro_func(*args_tuple)

                    results[index] = result
                    logger.info(f"Task-{index} ({coro_func_name}, {args_tuple}) completed.")
                except TimeoutError as exc:
                    logger.error(
                        error_msg := f"Task-{index} ({coro_func_name}, {args_tuple}) timed out after {timeout}s, err={exc}"
                    )
                    results[index] = error_msg
                except Exception as exc:
                    logger.error(error_msg := f"Task-{index} ({coro_func_name}, {args_tuple}) failed, err={exc}")
                    results[index] = error_msg

        try:
            async with anyio.create_task_group() as tg:
                for i, args in enumerate(args_tuple_list):
                    tg.start_soon(_wrapped, i, args)
        except Exception as e:
            logger.error(f"Task group execution failed, err={e}")
            # 确保返回完整的结果列表
            for i in range(len(args_tuple_list)):
                if results[i] is None:
                    results[i] = str(e)

        return results

    async def add_task(
            self,
            task_id: str,
            *,
            coro_func: Callable[..., Awaitable[Any]],
            args_tuple: tuple = (),
            kwargs_dict: dict | None = None,
            timeout: int | None = None,
    ) -> bool:
        kwargs_dict = kwargs_dict or {}
        coro_func_name = self.get_coro_func_name(coro_func)
        try:
            async with self.lock:
                if task_id in self.tasks:
                    logger.warning(f"Task {task_id} already exists.")
                    return False
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._run_task, task_id, coro_func, args_tuple, kwargs_dict, timeout)
                    self.tasks[task_id] = tg
                return True
        except Exception as e:
            logger.error(f"Error adding task {coro_func_name} for {task_id}, err={e}")
            return False

    async def cancel_task(self, task_id: str) -> bool:
        async with self.lock:
            tg: TaskGroup = self.tasks.get(task_id)
            if tg:
                tg.cancel_scope.cancel()
                logger.info(f"Task {task_id} cancelled.")
                return True
            logger.warning(f"Task {task_id} not found.")
            return False

    async def get_task_status(self) -> dict[str, bool]:
        async with self.lock:
            return {tid: not tg.cancel_scope.cancel_called for tid, tg in self.tasks.items()}

    async def shutdown(self):
        async with self.lock:
            task_groups = list(self.tasks.values())
            self.tasks.clear()

        logger.info(f"Shutting down {len(task_groups)} tasks...")
        try:
            for tg in task_groups:
                tg.cancel_scope.cancel()
            # 等待所有任务完成
            async with anyio.create_task_group() as tg:
                for t in task_groups:
                    tg.start_soon(lambda x: x.wait(), t)
        except Exception as e:
            logger.error(f"Error shutting down tasks. err={e}")

        logger.info("All tasks terminated")


# 全局实例
async_task_manager = AsyncTaskManager(max_tasks=100)
