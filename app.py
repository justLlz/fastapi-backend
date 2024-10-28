import time
import uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

from core.config import setting

from utils import response_utils
from utils.logger import logger


def create_app() -> FastAPI:
    app = FastAPI(debug=setting.DEBUG)

    # register_static_file(app)
    register_router(app)
    register_exception(app)
    register_middleware(app)

    return app


def register_static_file(app: FastAPI) -> None:
    app.mount('/assets', StaticFiles(directory='assets'), name='assets')


def register_router(app: FastAPI):
    from apps.asset_manage import router as assets_router
    app.include_router(assets_router, prefix='/asset_manage')


def register_exception(app: FastAPI):
    def _record_log_error(tag: str, err_desc: str):
        logger.error(f'{tag}: {err_desc}')

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        _record_log_error('Validation Error', err_desc := exc.__str__())
        return response_utils.resp_422(message=f'Validation Error: {err_desc}')

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException):
        _record_log_error('HTTP Error', err_desc := exc.__str__())
        return response_utils.custom_response(
            status_code=(code := exc.status_code),
            code=code,
            message=f'HTTP Error: {err_desc}',
            data=None
        )

    @app.exception_handler(Exception)
    async def all_exception_handler(_: Request, exc: Exception):
        _record_log_error('Internal Server Error', err_desc := exc.__str__())
        return response_utils.resp_500(message=f'Internal Server Error: {err_desc}')


def register_middleware(app: FastAPI):
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware)

    if setting.BACKEND_CORS_ORIGINS:
        from starlette.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=setting.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )

    @app.middleware('http')
    async def logger_request(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4().hex))

        with logger.contextualize(trace_id=trace_id):
            logger.info(f'access log: method:{request.method}, url:{request.url}, ip:{request.client.host}')

            start_time = time.perf_counter()
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Trace-ID"] = trace_id

            logger.info(
                f'response log: status_code:{response.status_code}, process_time:{process_time:.4f}s'
            )
        return response
