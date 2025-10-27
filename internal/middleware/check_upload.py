from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from pkg.resp_tool import response_factory

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next)-> Response:
        if request.url.path.startswith("/upload/"):
            # 读取请求体
            body = await request.body()
            if len(body) > MAX_UPLOAD_SIZE:
                return response_factory.resp_413(message="上传文件过大")
        return await call_next(request)
