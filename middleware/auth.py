import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config import setting
from utils.response_utils import resp_401


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 从请求头中提取 Authorization 字段
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return resp_401(message="Invalid or missing token")

        # 去掉前缀 "Bearer " 只保留 Token 部分
        token = token.split(" ")[1]

        # 校验和解码 Token，获取 user_id
        try:
            payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])
            user_id = payload.get("user_id")
            if user_id is None:
                return resp_401(message="Invalid token: user_id not found")

            # 将 user_id,user_name 存储在 request.state 中
            request.state.user_id = user_id
            request.state.user_name = payload.get("user_id", "")
        except jwt.ExpiredSignatureError:
            return resp_401(message="Token expired")
        except jwt.InvalidTokenError:
            return resp_401(message="Invalid token")

        # 继续处理请求
        response = await call_next(request)
        return response


class TokenAuthMiddleware2(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = 123
        request.state.user_name = 'root'
        # 继续处理请求
        response = await call_next(request)
        return response
