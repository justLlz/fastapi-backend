from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from config import setting

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
    # from apps.asset import router as assets_router
    # app.include_router(assets_router)
    # from apps.auth import router as auth_router
    # app.include_router(auth_router)
    # from apps.user import router as user_router
    # app.include_router(user_router)
    pass


def register_exception(app: FastAPI):
    def _record_log_error(tag: str, err_desc: str):
        logger.error(f'{tag}: {err_desc}')

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        _record_log_error('Validation Error', err_desc := exc.__str__())
        return response_utils.resp_422(message=f'Validation Error: {err_desc}')

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        _record_log_error('HTTP Error', err_desc := exc.__str__())
        return response_utils.custom_response(
            status_code=(code := exc.status_code),
            code=code.__str__(),
            message=f'HTTP Error: {err_desc}',
            data=None
        )

    @app.exception_handler(Exception)
    async def all_exception_handler(_: Request, exc: Exception):
        _record_log_error('Internal Server Error', err_desc := exc.__str__())
        return response_utils.resp_500(message=f'Internal Server Error: {err_desc}')


def register_middleware(app: FastAPI):
    # 4. GZip 中间件：压缩响应，提高传输效率
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware)

    # 3. 认证中间件：校验 Token，确保只有合法用户访问 API
    from middleware.auth import TokenAuthMiddleware2
    app.add_middleware(TokenAuthMiddleware2)

    # 2. 日志中间件：记录请求和响应的日志，监控 API 性能和请求流
    from middleware.logger import LoggerMiddleware
    app.add_middleware(LoggerMiddleware, logger=logger)

    # 1. CORS 中间件：处理跨域请求
    if setting.BACKEND_CORS_ORIGINS:
        from starlette.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=setting.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )
