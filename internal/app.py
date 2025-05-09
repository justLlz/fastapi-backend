import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError

from internal.config.setting import setting
from pkg import SYS_ENV, colorprint
from pkg.resp_helper import response_factory


def create_app() -> FastAPI:
    debug = setting.DEBUG
    app = FastAPI(
        debug=debug,
        docs_url="/docs" if debug else None,
        redoc_url="/redoc" if debug else None,
        lifespan=lifespan
    )

    register_router(app)
    register_exception(app)
    register_middleware(app)

    return app


def register_router(app: FastAPI):
    from internal.controller.test import router as test_router
    app.include_router(test_router)


def register_exception(app: FastAPI):
    def _record_log_error(tag: str, err_desc: str):
        logging.error(f"{tag}: {err_desc}")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        _record_log_error("Validation Error", repr(exc))
        return response_factory.resp_422(message=f"Validation Error: {exc}")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        return response_factory.response(code=exc.status_code, message=exc.detail)


def register_middleware(app: FastAPI):
    # 6. GZip 中间件：压缩响应，提高传输效率
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware)

    # 5. 限制上传文件大小
    # from internal.middleware.upload_size import LimitUploadSizeMiddleware
    # app.add_middleware(LimitUploadSizeMiddleware)

    # 4. 认证中间件：校验 Token，确保只有合法用户访问 API
    from internal.middleware.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware)

    from internal.middleware.exception import ExceptionHandlingMiddleware
    # 3. 异常处理中间件（需继承 BaseHTTPMiddleware）
    app.add_middleware(ExceptionHandlingMiddleware)

    # 2. 日志中间件：记录请求和响应的日志，监控 API 性能和请求流
    from internal.middleware.recorder import RecorderMiddleware
    app.add_middleware(RecorderMiddleware)

    # 1. CORS 中间件：处理跨域请求
    if setting.BACKEND_CORS_ORIGINS:
        from starlette.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=setting.BACKEND_CORS_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )


# 定义 lifespan 事件处理器
@asynccontextmanager
async def lifespan(_app: FastAPI):
    colorprint.green("Init lifespan...")
    # 检查环境变量
    if SYS_ENV not in ["local", "dev", "test", "prod"]:
        raise Exception(f"Invalid ENV: {SYS_ENV}")

    colorprint.green("Check completed, Application will start.")
    # 进入应用生命周期
    yield
    # 关闭时的清理逻辑
    colorprint.blue("Application is about to close.")
