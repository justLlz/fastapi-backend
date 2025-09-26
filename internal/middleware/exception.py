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

        if scope_type == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope_type == "http":
            response_started = False
            response_ended = False

            async def send_wrapper(message):
                nonlocal response_started, response_ended
                msg_type = message.get("type")
                if msg_type == "http.response.start":
                    response_started = True
                elif msg_type == "http.response.body":
                    if not message.get("more_body", False):
                        response_ended = True
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as exc:
                logger.error(f"Exception occurred:\n{get_last_exec_tb(exc)}")

                if response_started:
                    if not response_ended:
                        try:
                            await send(
                                {"type": "http.response.body", "body": b"", "more_body": False}
                            )
                        except Exception:
                            pass
                    return

                if isinstance(exc, AppException):
                    resp = response_factory.response(code=exc.code, msg=exc.detail)
                else:
                    resp = response_factory.resp_500()

                await resp(scope, receive, send)
                return

        await self.app(scope, receive, send)
