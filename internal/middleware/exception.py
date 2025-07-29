import traceback

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from pkg.exception import AppHTTPException, AppIgnoreException
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
            if isinstance(exc, AppHTTPException | HTTPException):
                response = response_factory.response(code=exc.status_code, msg=exc.detail)
            elif isinstance(exc, AppIgnoreException):
                response = response_factory.resp_500()
            else:
                tb_lines = traceback.format_exc().strip().split("\n")
                last_3_lines = tb_lines[-5:] if len(tb_lines) >= 5 else tb_lines
                logger.error(f'''Exception occurred: {type(exc).__name__}={exc}.\n{"\n".join(last_3_lines)}''')
                response = response_factory.resp_500()
            await response(scope, receive, send)
