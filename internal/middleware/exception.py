import traceback

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from pkg.logger_helper import logger
from pkg.resp_helper import response_factory


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except BaseException as exc:
            logger.error(f"Exception: {traceback.format_exc()}")
            return response_factory.resp_500(message=str(exc))
