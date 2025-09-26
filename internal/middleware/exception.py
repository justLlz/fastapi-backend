from starlette.types import ASGIApp, Receive, Scope, Send

from internal.utils.exception import AppException, get_last_exec_tb
from pkg.logger_helper import logger
from pkg.resp_helper import response_factory


class ExceptionHandlerMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if (scope_type := scope["type"]) == "websocket":
            await self.app(scope, receive, send)
            return
        elif scope_type == "lifespan":
            await self.app(scope, receive, send)
            return
        elif scope_type == "http":
            try:
                await self.app(scope, receive, send)
            except Exception as exc:
                logger.error(f'''Exception occurred:\n{get_last_exec_tb(exc)}''')
                if isinstance(exc, AppException):
                    response = response_factory.response(code=exc.code, msg=exc.detail)
                else:
                    response = response_factory.resp_500()
                await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
