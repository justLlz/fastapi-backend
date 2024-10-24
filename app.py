from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from core.config import setting
from core.db import lifespan
from utils import response_code
from utils.logger import logger
from utils.response_code import CustomORJSONResponse


def create_app():
    """
    fastapi工厂模式
    """
    app = FastAPI(debug=setting.DEBUG, lifespan=lifespan)
    # openapi_url=f'{settings.API_V1_STR}/openapi.json'

    # 其余的一些全局配置可以写在这里 多了可以考虑拆分到其他文件夹

    # 跨域设置
    register_cors(app)

    # 注册路由
    register_router(app)

    # 注册捕获全局异常
    register_exception(app)

    # 请求拦截
    # register_middleware(app)

    # if settings.DEBUG:
    #     # 注册静态文件
    #     pass
    # register_static_file(app)

    return app


def register_static_file(app: FastAPI) -> None:
    """
    静态文件交互 生产使用 nginx
    这里是开发是方便本地
    :param app:
    :return:
    """
    from fastapi.staticfiles import StaticFiles
    app.mount('/assets', StaticFiles(directory='assets'), name='assets')


def register_router(app: FastAPI):
    """
    注册路由
    :param app:
    :return:
    """

    from apps.asset_manage import router as assets_router
    app.include_router(assets_router, prefix='/asset_manage')


def register_cors(app: FastAPI):
    """
    支持跨域

    :param app:
    :return:
    """

    if setting.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,  # type: ignore
            allow_origins=setting.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )


def register_exception(app: FastAPI):
    """
    全局异常捕获
    :param app:
    :return:
    """

    def _record_log_error(request: Request, tag: str, err: str):
        logger.error(
            f'{tag}:\nmethod: {request.method}\nurl: {request.url}\nheaders: {request.headers}\nerr: {err}')

    # 捕获 Pydantic 校验错误
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        :param request:
        :param exc:
        :return:
        """
        tag = 'Validation Error'
        _record_log_error(request, tag, err_desc := exc.__str__())
        return response_code.resp_422(message=f'{tag}: {err_desc}')

    # 捕获 HTTP 异常
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        :param request:
        :param exc:
        :return:
        """
        tag = 'HTTP Error'
        _record_log_error(request, tag, err_desc := exc.__str__())
        return CustomORJSONResponse(
            status_code=exc.status_code,
            content={
                'code': exc.status_code,
                'message': f'{tag}: {err_desc}',
                'data': None
            }
        )

    # 捕获其他所有异常
    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        """
        全局所有异常, Debug模式下不会被捕获
        :param request:
        :param exc:
        :return:
        """
        tag = 'Internal Server Error'
        _record_log_error(request, tag, err_desc := exc.__str__())
        return response_code.resp_500(message=f'{tag}: {err_desc}')


def register_middleware(app: FastAPI):
    """
    请求响应拦截 hook

    https://fastapi.tiangolo.com/tutorial/middleware/
    :param app:
    :return:
    """

    @app.middleware('http')
    async def logger_request(request: Request, call_next):
        # https://stackoverflow.com/questions/60098005/fastapi-starlette-get-client-real-ip
        # logger.info(f'访问记录:{request.method} url:{request.url}\nheaders:{request.headers}\nIP:{request.client.host}')

        response = await call_next(request)

        return response
