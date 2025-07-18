from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from pkg.exception import AppIgnoreException
from pkg.logger_helper import logger
from pkg.resp_helper import response_factory


class ExceptionHandlingMiddleware:
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
            if not isinstance(exc, AppIgnoreException):
                logger.exception("Exception occurred: ")
            response = response_factory.resp_500(message=str(exc))
            await response(scope, receive, send)
