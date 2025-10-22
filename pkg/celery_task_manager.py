from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any, cast

from celery import Celery, chain, chord, group, signals, states
from celery.result import AsyncResult, GroupResult
from kombu.utils.uuid import uuid

from pkg.logger_helper import logger


class CeleryClient:
    """
    一个面向 FastAPI 的 Celery 工具类，封装常见操作：
    - 初始化 Celery 实例
    - 提交任务：立即 / 倒计时 / ETA / 自定义 options（重试、过期、队列、路由等）
    - 查询任务状态与结果
    - 撤销/终止任务
    - 任务编排：chain / group / chord
    - worker 运行态检查：active/reserved/scheduled/stats

    示例：
        celery_client = CeleryClient(
            app_name="my_fastapi_app",
            broker_url="redis://localhost:6379/0",
            backend_url="redis://localhost:6379/1",
            include=["tasks"],  # 你的任务模块列表
        )
        r = celery_client.submit("tasks.add", (1, 2))
        print(r.id, r.status)
    """

    def __init__(
            self,
            app_name: str,
            broker_url: str,
            backend_url: str | None = None,
            include: Sequence[str] | None = None,
            task_routes: Mapping[str, Mapping[str, Any]] | None = None,
            task_default_queue: str = "default",
            timezone: str = "UTC",
            result_expires: int | float | timedelta = timedelta(hours=1),
            task_serializer: str = "json",
            accept_content: Sequence[str] | None = ("json",),
            result_serializer: str = "json",
            enable_utc: bool = True,
            broker_connection_retry_on_startup: bool = True,
            **extra_conf: Any,
    ) -> None:
        """
        初始化一个面向 FastAPI 的 Celery 客户端，并设置常见运行参数。

        参数
        ----
        app_name : str
            Celery 应用名（同时作为任务名前缀空间的一部分）。用来区分不同应用实例。
            例：'fastapi_celery_demo'。

        broker_url : str
            Broker（消息中间件）连接串。用于发布/消费任务消息。
            常见：
              - Redis：'redis://localhost:6379/0'
              - RabbitMQ：'amqp://user:pass@host:5672/vhost'

        backend_url : str | None
            结果后端（result backend）连接串。用于存储任务状态与结果；为 None 时部分功能（如 .get()）不可用。
            常见：
              - Redis：'redis://localhost:6379/1'
              - 数据库：'db+postgresql://user:pass@host/dbname'
            注意：生产环境建议使用持久后端，便于查询与幂等对账。

        include : Sequence[str] | None
            需要在启动时**主动导入**的 Python 模块列表（import path），用于完成任务注册。
            写的是“可导入的模块路径”，不是文件系统路径。
            例：
              - ['tasks']（同目录 tasks.py）
              - ['myproj.workers.tasks']（包内模块）
            提示：它不会递归导入子模块；若有多个模块，逐个列出或在包的 __init__.py 中显式导入。

        task_routes : dict[str, dict[str, str]] | None
            任务路由表：按任务名（字符串）指定投递选项（队列、routing_key、exchange 等）。
            Key 是任务名（通常为 '模块名.函数名'），Value 是路由配置。
            例：
              {
                'tasks.add': {'queue': 'math'},
                'reports.generate': {'queue': 'io', 'routing_key': 'io'},
              }
            支持通配（如 'tasks.*'）。只有监听了该队列的 worker 才会消费。

        task_default_queue : str
            默认队列名。未匹配到路由规则的任务会投递到这里。
            配合 worker 的 -Q 参数控制实际监听的队列集合。

        timezone : str
            时区标识（IANA/Olson），用于 ETA、定时任务等时间相关行为。
            例：'UTC'、'Asia/Shanghai'。当 enable_utc=True 时，内部以 UTC 存储，显示/解析按该时区。

        result_expires : int | float | timedelta
            任务结果过期时间（缓存 TTL）。可用秒数或 timedelta。
            影响 result backend 中结果保留时长，过期后 .get() 可能拿不到历史结果。

        task_serializer : str
            任务消息序列化格式。常用 'json'。生产环境不建议启用 pickle 以避免安全风险。

        accept_content : Sequence[str] | None
            Worker 可接受的消息内容类型白名单。
            默认 ('json',)，用于防止误收不安全/不兼容的消息。

        result_serializer : str
            结果序列化格式。常用 'json'。需与 result backend 的解码能力匹配。

        enable_utc : bool
            是否启用 UTC 基准时间。一般保持 True；显示与解析受 timezone 影响。
            若业务严格按本地时区处理 ETA/定时，可配合 timezone 调整。

        broker_connection_retry_on_startup : bool
            启动时连接 broker 失败是否重试（发布层重试）。部署在容器编排环境时建议 True，提升冷启动容错性。

        extra_conf : Any
            其它 Celery 配置的透传入口。会合并到 app.conf 中（后写覆盖前写）。
            例：task_queues、task_annotations、task_time_limit、worker_concurrency、imports、broker_transport_options 等。

        备注
        ----
        - `{"queue": "math"}` 的含义是把匹配到的任务投递到名为 'math' 的队列；需要 worker 使用 `-Q math`
          或 `-Q default,math` 监听该队列才能消费。
        - `include` 与 `task_routes` 关注点不同：前者是**导入模块注册任务**，后者是**把已注册的任务路由到具体队列**。
        - Redis 做 result backend 时，`result_expires` 也影响键的过期；过短会导致历史查询不到结果。
        """
        self.queue = task_default_queue
        self.app = Celery(app_name, broker=broker_url, backend=backend_url, include=include)

        # 默认配置
        conf = {
            "timezone": timezone,
            "enable_utc": enable_utc,
            "task_default_queue": task_default_queue,
            "task_routes": task_routes or {},
            "result_expires": result_expires,
            "task_serializer": task_serializer,
            "accept_content": list(accept_content or ("json",)),
            "result_serializer": result_serializer,
            "worker_hijack_root_logger": False,
            "broker_connection_retry_on_startup": broker_connection_retry_on_startup,
            "result_extended": True
        }
        conf.update(extra_conf or {})
        self.app.conf.update(conf)

    # ------------------------------
    # 提交/编排任务
    # ------------------------------
    def submit(
            self,
            *,
            task_id: str | None = None,
            task_name: str,
            args_tuple: tuple | list | Any | None = None,
            kwargs_dict: dict | None = None,
            countdown: int | float | None = None,
            eta: datetime | None = None,
            expires: int | float | datetime | None = None,
            priority: int | None = None,
            routing_key: str | None = None,
            retry: dict | None = None,  # 你自定义的“软重试”载荷，放进 headers["x-retry"]
            publish_retry: bool | None = False,  # 发布层（producer）重试
            publish_retry_policy: dict | None = None,
            **options: Any,  # 透传给 send_task 的其它参数（如 shadow/link/link_error/time_limit 等）
    ) -> AsyncResult:
        """
        统一的任务提交入口（基于 Celery canvas/signature）。
        典型用法：
          - 立即执行：submit(task_name="tasks.add", args_tuple=(1, 2))
          - 倒计时执行：submit(task_name="tasks.add", args_tuple=(1, 2), countdown=10)
          - 指定 ETA：submit(task_name="tasks.add", args_tuple=(1, 2), eta=datetime.utcnow()+timedelta(seconds=30))
          - 通过自定义 header 传“运行时重试策略”：retry={"max_retries": 3, "countdown": 5}

        参数
        ----
        task_id : str | None
            自定义任务 ID（默认自动生成 UUID）。用于**幂等/去重**与**结果查询**。
            注意：ID 必须在全局唯一；重复 ID 不会自动“覆盖”，可能造成结果混淆，请自行保证唯一性。

        task_name : str
            任务的注册名（通常是 "模块名.函数名"，如 "tasks.add"）。必须与 worker 侧注册的任务名一致。

        args_tuple : Any
            位置参数集合，**建议传 tuple 或 list**，会作为 `*args` 传给任务函数。
            只有一个参数时也请写成单元素 tuple：`(x,)`，避免歧义。

        kwargs : dict
            关键字参数字典，默认为 `{}`（内部会把 None 转为空字典）。

        countdown : int | float | None
            从“现在”起延迟多少秒再执行（与 `eta` 互斥；若两者都给，通常以 `eta` 为准）。

        eta : datetime | None
            任务的**绝对**计划执行时间点。建议使用 UTC 时间（或与应用 `timezone`/`enable_utc` 配置保持一致）。

        expires : int | float | datetime | None
            任务过期时间：可传相对秒数或绝对时间。
            过期后任务将被丢弃/拒绝执行（常见为标记为已撤销/过期），用于限制排队过久的任务。

        priority : int | None
            任务优先级（通常 0~9，数值越大优先级越高；取决于 broker 配置）。
            - RabbitMQ：需要队列声明了 `x-max-priority`，并设置 `task_queue_max_priority`。
            - Redis：优先级为“模拟/近似”，效果视 Celery/transport 版本而定。

        queue : str | None
            目标队列名（例如 "math"）。只有**监听了该队列**的 worker 才会消费：
            `celery -A celery_app.app worker -Q default,math -l info`。

        routing_key : str | None
            路由键（与交换机/队列绑定规则相关）。在直连交换机下通常与 `queue` 同名；只有需要精细 AMQP 路由时才需要显式指定。

        retry : dict
            **自定义“运行时重试策略”载荷**，会被注入到消息 `headers["x-retry"]` 中，供任务函数（`bind=True`）自行读取并调用
            `self.retry(...)` 实现重试。例如：`{"max_retries": 3, "countdown": 5}`。
            注意：这**不是** `apply_async` 的“发布层（publish）重试”参数；发布层重试请通过 `**options` 传 `retry=True/retry_policy={...}`。

        **options : Any
            透传给 `signature(...).apply_async(**options)` 的其它参数。
            常见如：`serializer`、`compression`、`link`（成功回调）、`link_error`（失败回调）、
            `shadow`、`time_limit`、`soft_time_limit`、`retry`（发布层重试）、`retry_policy` 等。
            若你也想传自定义 headers，请扩展本函数合并到内部 headers 后再调用。

        返回
        ----
        AsyncResult
            任务结果句柄，可用于 `.id`、`.status`、`.ready()`、`.get()` 等。

        说明
        ----
        - 本函数会把 `retry` 字段打包到 `headers["x-retry"]`，在任务内可通过
          `from celery import current_task; current_task.request.headers.get("x-retry")` 读取，并自行调用 `self.retry(...)`。
        - `countdown` 与 `eta` 语义互斥，提供 `eta` 更明确；时间基准受 `timezone`/`enable_utc` 影响。
        - 若需要跨服务调用且本进程未注册该任务，考虑退化为 `app.send_task(...)` 的路径。
        """
        task_id = task_id or uuid()
        logger.info(f"Submitting task {task_name} with id {task_id}")

        if eta:
            countdown = None

        if args_tuple is None:
            task_args: tuple = ()
        else:
            if isinstance(args_tuple, (tuple, list)):
                task_args = tuple(args_tuple)
            else:
                task_args = (args_tuple,)

        task_kwargs = dict(kwargs_dict or {})

        # ---- headers：进 request.headers，可在任务里 self.request.headers 获取
        msg_headers: dict[str, Any] = {}
        if retry:
            msg_headers["x-retry"] = retry
        # 允许调用者通过 options 追加/覆盖 headers（必须是可 JSON 序列化的简单类型）
        user_headers = options.pop("headers", {})
        if user_headers:
            msg_headers.update(user_headers)

        # ---- 发布层重试策略
        if publish_retry:
            default_retry_policy = {
                "max_retries": 5,
                "interval_start": 1,
                "interval_step": 2,
                "interval_max": 10,
            }
            options.setdefault("retry", True)
            options.setdefault("retry_policy", publish_retry_policy or default_retry_policy)

        # ---- 真正发送（返回 AsyncResult）
        return self.app.send_task(
            name=task_name,
            args=task_args,
            kwargs=task_kwargs,
            task_id=task_id,
            countdown=countdown,
            eta=eta,
            expires=expires,
            priority=priority,
            routing_key=routing_key,
            headers=msg_headers,
            **options,
        )

    def submit_countdown(
            self, *, task_id: str | int, task_name: str, seconds: int | float, args_tuple: tuple, **kw: Any
    ) -> AsyncResult:
        """
        倒计时执行：
        用法：client.submit_countdown("tasks.add", 10, (1, 2))
        """
        return self.submit(task_id=task_id, task_name=task_name, args_tuple=args_tuple, countdown=seconds, **kw)

    def submit_eta(
            self, *, task_id: str | int, task_name: str, eta: datetime, args_tuple: tuple, **kw: Any
    ) -> AsyncResult:
        """
        指定 ETA 执行：
        用法：client.submit_eta("tasks.add", datetime.utcnow()+timedelta(seconds=10), (1, 2))
        """
        return self.submit(task_id=task_id, task_name=task_name, args_tuple=args_tuple, eta=eta, **kw)

    @staticmethod
    def chain(*task_sigs: Any) -> AsyncResult:
        """
        chain：前一个任务的返回作为下一个任务的输入。
        用法：client.chain(sig("tasks.add", (1, 2)), sig("tasks.mul", (3,)))
        """
        return chain(*task_sigs).apply_async()

    @staticmethod
    def group(*task_sigs: Any, group_id: str | None = None) -> GroupResult:
        """
        group：并行执行一组任务。
        用法：client.group(sig("tasks.add", (1, 2)), sig("tasks.add", (3, 4))
        """
        g = group(*task_sigs).apply_async(group_id=group_id)
        return cast(GroupResult, cast(object, g))

    @staticmethod
    def chord(
            header_sigs: Iterable[Any], body_sig: Any, group_id: str | None = None
    ) -> AsyncResult:
        """
        chord：header（group 并行）全部完成后，再触发 body。
        用法：client.chord([sig("tasks.add",(1,2)), sig("tasks.add",(3,4))], sig("tasks.sum_list"))
        """
        return chord(header_sigs)(body_sig).apply_async(group_id=group_id)

    # ------------------------------
    # 查询/管理任务
    # ------------------------------
    def async_result(self, task_id: str) -> AsyncResult:
        return AsyncResult(task_id, app=self.app)

    def info(self, task_id: str) -> dict[str, Any]:
        """
        返回更详细的状态信息（status、result/traceback、ready/success 等）。
        """
        r: AsyncResult = AsyncResult(task_id)
        payload: dict[str, Any] = {
            "id": task_id,
            "status": r.state,
            "ready": r.ready(),
            "successful": r.successful() if r.ready() else None,
            "failed": r.failed() if r.ready() else None,
        }

        # 统一返回 result（成功时是返回值；失败时是结构化 error）
        if r.state == states.SUCCESS:
            payload["result"] = r.result
            payload["traceback"] = None
        elif r.state == states.FAILURE:
            payload["error"] = self._extract_failure(r)  # <— 关键：结构化异常信息
            payload["result"] = None  # 避免前端混淆
        else:
            # PENDING / STARTED / RETRY / REVOKED 等
            # 可选：把 r.info（进度/中间状态）也透出
            # r.info 在失败时等于异常；在运行中可能是自定义进度 dict
            info_obj = r.info
            payload["result"] = info_obj if not isinstance(info_obj, BaseException) else None
            payload["error"] = self._extract_failure(r)
            payload["traceback"] = None

        return payload

    def status(self, task_id: str) -> str:
        return self.async_result(task_id).status

    def is_ready(self, task_id: str) -> bool:
        """
        检查任务是否完成

        Args:
            task_id: 任务ID

        Returns:
            bool: 任务是否完成
        """
        r: AsyncResult = self.async_result(task_id)
        return r.ready()

    def is_successful(self, task_id: str) -> bool:
        """
        检查任务是否成功完成

        Args:
            task_id: 任务ID

        Returns:
            bool: 任务是否成功
        """
        r: AsyncResult = self.async_result(task_id)
        return r.successful() if r.ready() else None

    def is_failed(self, task_id: str) -> bool:
        """
        检查任务是否失败

        Args:
            task_id: 任务ID

        Returns:
            bool: 任务是否失败
        """
        r: AsyncResult = self.async_result(task_id)
        return r.failed() if r.ready() else None

    def revoke(self, task_id: str, terminate: bool = False, signal: str = "SIGTERM") -> None:
        """
        撤销任务；若 terminate=True 则尝试发送信号终止正在执行的任务（需 worker 配合）。
        """
        self.app.control.revoke(task_id, terminate=terminate, signal=signal)

    # ------------------------------
    # Worker 运行态检查
    # ------------------------------
    def inspect_active(self) -> dict[str, Any]:
        return self.app.control.inspect().active() or {}

    def inspect_reserved(self) -> dict[str, Any]:
        return self.app.control.inspect().reserved() or {}

    def inspect_scheduled(self) -> dict[str, Any]:
        return self.app.control.inspect().scheduled() or {}

    def inspect_stats(self) -> dict[str, Any]:
        return self.app.control.inspect().stats() or {}

    @staticmethod
    def _extract_failure(r: AsyncResult) -> dict[str, Any] | None:
        if r.state != states.FAILURE:
            return None

        # 先尝试把异常当成真正的 Exception 来读
        err = r.result
        if isinstance(err, Exception):
            return {
                "type": err.__class__.__name__,
                "module": err.__class__.__module__,
                "message": repr(err),  # 比 repr 更适合给人看
                "args": getattr(err, "args", ()),
                "traceback": r.traceback,
            }

        # 否则回退到后端原始 meta（Redis/DB 会带 exc_type/ exc_message）
        meta = r.backend.get_task_meta(r.id)  # 公共 API
        msg = None
        exc_msg = meta.get("exc_message")
        if isinstance(exc_msg, (list, tuple)):
            msg = " ".join(map(str, exc_msg))
        elif isinstance(exc_msg, str):
            msg = exc_msg

        return {
            "type": meta.get("exc_type") or getattr(err, "__class__", type(err)).__name__,
            "module": meta.get("exc_module"),
            "message": msg or str(err),
            "traceback": meta.get("traceback") or r.traceback,
            "raw_result": err,  # 视需要可去掉
        }


@signals.worker_process_init.connect
def _init_db_in_worker_process_init(**_):
    # init_func()
    logger.info("worker_process_init success")


@signals.worker_process_shutdown.connect
def _close_db_in_worker_process_init(**_):
    # 可选：优雅关闭
    import asyncio
    try:
        asyncio.get_running_loop()
        # close_func()
    except RuntimeError:
        # 没有 loop 就开一个临时的
        # asyncio.run(close_func())
        ...
    else:
        # 有 loop 就直接 await
        # （如果这里在 Celery 回调里不能直接 await，就也用 asyncio.run）
        pass


@signals.worker_init.connect
def _init_db_in_worker_init(**_):
    # init_func()
    logger.info("worker_init success")


@signals.worker_shutdown.connect
def _close_db_in_worker_shutdown(**_):
    # 可选：优雅关闭
    import asyncio
    try:
        asyncio.get_running_loop()
        # close_func()
    except RuntimeError:
        # 没有 loop 就开一个临时的
        # asyncio.run(close_func())
        ...
    else:
        # 有 loop 就直接 await
        # （如果这里在 Celery 回调里不能直接 await，就也用 asyncio.run）
        pass
