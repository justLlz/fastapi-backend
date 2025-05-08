import time
import traceback
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from pkg.logger_helper import logger
from pkg.resp_helper import response_factory


class RecorderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 获取 trace_id，若不存在则生成一个新的
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4().hex))

        # 使用 logger 上下文管理器
        with logger.contextualize(trace_id=trace_id):
            try:
                # 记录访问日志
                logger.info(
                    f"access log: ip: {request.client.host}, method: {request.method}, path: {request.url.path}, params: {dict(request.query_params)}"
                )

                # 开始计时
                start_time = time.perf_counter()
                response = await call_next(request)  # 调用下一个中间件或路由处理函数
                process_time = time.perf_counter() - start_time

                # 将处理时间和 trace_id 写入响应头
                response.headers["X-Process-Time"] = str(process_time)
                response.headers["X-Trace-ID"] = trace_id

                # 记录响应日志
                logger.info(
                    f"response log: {response.status_code}, process_time: {process_time:.4f}s"
                )
            except Exception as e:
                logger.error(f"Unhandled Exception: {traceback.format_exc()}")
                return response_factory.resp_500(message=f"Unhandled Exception: {str(e)}")

        return response
