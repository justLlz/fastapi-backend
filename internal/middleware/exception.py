import traceback

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from pkg.resp import response_factory


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(f"Unhandled Exception: {traceback.format_exc()}")
            return response_factory.resp_500(message=f"Unhandled Exception: {str(exc)}")
