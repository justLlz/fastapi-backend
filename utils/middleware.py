from configparser import ConfigParser

from starlette.datastructures import Headers, URL
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from utils.logger import logger

WHITE_LIST = []


def check_devops_auth(token: str):
    pass


class AuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        logger.info(scope.get('path'))
        if scope.get('path'):
            url = URL(scope=scope)
            if url.path not in WHITE_LIST:  # 设置白名单
                headers = Headers(scope=scope)
                token = headers.get("Token")
                # 自定义访问拦截
                if not token or not headers.get("username") or not check_devops_auth(token):  # 自定义验证token，和其他请求信息作为认证拦截
                    response = PlainTextResponse("未登陆用户", status_code=401)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)
