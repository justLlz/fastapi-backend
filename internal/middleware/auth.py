from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from internal.core.session import verify_session
from internal.core.signature import verify_signature
from pkg.resp import resp_401

not_auth_session_path = [
    "/auth/login",
    "/auth/register",
    "/docs",
    "/openapi.json",
    "/v1/auth/login_by_account",
    "/v1/auth/login_by_phone",
    "/v1/auth/verify_session"
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        url_path = request.url.path
        # openapi验签逻辑
        if url_path.startswith("/openapi") and url_path != "/openapi.json":
            x_signature = request.headers.get("X-Signature", "")
            x_timestamp = request.headers.get("X-Timestamp", "")
            x_nonce = request.headers.get("X-Nonce", "")
            if not await verify_signature(x_signature, x_timestamp, x_nonce):
                return resp_401(message="invalid signature or timestamp")
            return await call_next(request)

        # 跳过无需认证的路径
        if url_path in not_auth_session_path or url_path.startswith("/test"):
            return await call_next(request)

        # session 校验
        session = request.headers.get("Authorization")
        user_data, ok = await verify_session(session)
        if not ok:
            return resp_401(message="invalid or missing session")

        request.state.user_data = user_data
        return await call_next(request)
