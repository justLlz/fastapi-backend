from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from pkg.resp import resp_413

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/upload/"):
            # 读取请求体
            body = await request.body()
            if len(body) > MAX_UPLOAD_SIZE:
                return resp_413(message="上传文件过大")
        response = await call_next(request)
        return response
