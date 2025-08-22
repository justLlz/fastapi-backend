from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from internal.utils.exception import AppException, AppIgnoreException, get_last_exec_tb
from pkg.logger_helper import logger
from pkg.resp_helper import response_factory


class ExceptionHandlerMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        _ = Request(scope, receive=receive)
        try:
            await self.app(scope, receive, send)
        except BaseException as exc:
            logger.error(f'''Exception occurred:\n{get_last_exec_tb(exc)}''')
            if isinstance(exc, AppException | HTTPException):
                response = response_factory.response(code=exc.status_code, msg=exc.detail)
            elif isinstance(exc, AppIgnoreException):
                response = response_factory.resp_500()
            else:
                response = response_factory.resp_500()
            await response(scope, receive, send)
