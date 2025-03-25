import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, HTTPException

from internal.setting import setting
from pkg import colorprint, get_sys_env_var, handle_resp


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

    # 清除uvicorn相关日志记录器的默认处理日志处理器
    # logging.getLogger("uvicorn.access").handlers = []
    # logging.getLogger("uvicorn.error").handlers = []
    # logging.getLogger("uvicorn").handlers = []
    return app


def register_router(app: FastAPI):
    from internal.controllers.test import router as test_router
    app.include_router(test_router)


def register_exception(app: FastAPI):
    def _record_log_error(tag: str, err_desc: str):
        logging.error(f"{tag}: {err_desc}")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        _record_log_error("Validation Error", repr(exc))
        return handle_resp.resp_422(message=f"Validation Error: {exc}")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        exec_detail, exec_status_code = exc.detail, exc.status_code
        return handle_resp.custom_response(
            status_code=exec_status_code,
            code=str(exec_status_code),
            message=exec_detail,
            data=None
        )

    @app.exception_handler(Exception)
    async def all_exception_handler(_: Request, exc: Exception):
        _record_log_error("Internal Server Error", repr(exc))
        return handle_resp.resp_500(message=f"Internal Server Error: {exc}")


def register_middleware(app: FastAPI):
    # 6. GZip 中间件：压缩响应，提高传输效率
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware)

    # 5. 异常处理中间件：处理异常，返回统一的错误响应
    from internal.middleware.exception import ExceptionHandlingMiddleware
    app.add_middleware(ExceptionHandlingMiddleware)

    # 4. 限制上传文件大小
    from internal.middleware.limit_upload_size import LimitUploadSizeMiddleware
    app.add_middleware(LimitUploadSizeMiddleware)

    # 3. 认证中间件：校验 Token，确保只有合法用户访问 API
    from internal.middleware.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware)

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
    env_var = get_sys_env_var()
    if env_var not in ["dev", "test", "prod", "local"]:
        colorprint.red(f"Invalid FAST_API_ENV value: {env_var}")
        sys.exit(1)

    colorprint.green("Check completed, Application will start.")
    # 进入应用生命周期
    yield
    # 关闭时的清理逻辑
    colorprint.blue("Application is about to close.")
