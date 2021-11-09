"""

fastapi工厂模式

"""
import traceback

import aioredis
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, ValidationError

from common.logger import logger
from utils.custom_exc import PostParamsError, UserTokenError, UserNotFound
from utils import response_code

from settings.config import settings


def create_app():
    """
    生成FatAPI对象
    """
    app = FastAPI()
    # title=settings.PROJECT_NAME,
    # description=settings.DESCRIPTION,
    # docs_url=f"{settings.API_V1_STR}/docs",
    # openapi_url=f"{settings.API_V1_STR}/openapi.json"

    # 其余的一些全局配置可以写在这里 多了可以考虑拆分到其他文件夹

    # 跨域设置
    # register_cors(app)

    # 注册路由
    # register_router(app)
    from apps import index
    app.include_router(index.router, prefix='')

    from apps import user
    app.include_router(user.router, prefix='')

    # 注册捕获全局异常
    # register_exception(app)

    # 请求拦截
    # register_middleware(app)

    # 挂载redis
    # register_redis(app)

    if settings.DEBUG:
        # 注册静态文件
        pass
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
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")


def register_router(app: FastAPI):
    """
    注册路由
    这里暂时把两个API服务写到一起，后面在拆分
    :param app:
    :return:
    """
    # 项目API
    from apps import index
    app.include_router(index.router, prefix='')

    from apps import user
    app.include_router(user.router, prefix='')


def register_cors(app: FastAPI):
    """
    支持跨域

    :param app:
    :return:
    """
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def register_exception(app: FastAPI):
    """
    全局异常捕获

    注意 别手误多敲一个s

    exception_handler
    exception_handlers
    两者有区别

        如果只捕获一个异常 启动会报错
        @exception_handlers(UserNotFound)
    TypeError: 'dict' object is not callable

    :param app:
    :return:
    """

    # 自定义异常 捕获
    @app.exception_handler(UserNotFound)
    async def user_not_found_exception_handler(request: Request, exc: UserNotFound):
        """
        用户认证未找到
        :param request:
        :param exc:
        :return:
        """
        logger.error(
            f"token未知用户\nURL:{request.method}{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")

        return response_code.resp_5001(message=exc.err_desc)

    @app.exception_handler(UserTokenError)
    async def user_token_exception_handler(request: Request, exc: UserTokenError):
        """
        用户token异常
        :param request:
        :param exc:
        :return:
        """
        logger.error(f"用户认证异常\nURL:{request.method}{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")

        return response_code.resp_5000(message=exc.err_desc)

    @app.exception_handler(PostParamsError)
    async def query_params_exception_handler(request: Request, exc: PostParamsError):
        """
        内部查询操作时，其他参数异常
        :param request:
        :param exc:
        :return:
        """
        logger.error(f"参数查询异常\nURL:{request.method}{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")

        return response_code.resp_400(message=exc.err_desc)

    @app.exception_handler(ValidationError)
    async def inner_validation_exception_handler(request: Request, exc: ValidationError):
        """
        内部参数验证异常
        :param request:
        :param exc:
        :return:
        """
        logger.error(
            f"内部参数验证错误\nURL:{request.method}{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")
        return response_code.resp_500(message=exc.errors())

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        请求参数验证异常
        :param request:
        :param exc:
        :return:
        """
        logger.error(
            f"请求参数格式错误\nURL:{request.method}{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")
        return response_code.resp_422(message=exc.errors())

    # 捕获全部异常
    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        """
        全局所有异常
        :param request:
        :param exc:
        :return:
        """
        logger.error(f"全局异常\n{request.method}URL:{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")
        return response_code.resp_500(message="服务器内部错误")


def register_middleware(app: FastAPI):
    """
    请求响应拦截 hook

    https://fastapi.tiangolo.com/tutorial/middleware/
    :param app:
    :return:
    """

    @app.middleware("http")
    async def logger_request(request: Request, call_next):
        # https://stackoverflow.com/questions/60098005/fastapi-starlette-get-client-real-ip
        # logger.info(f"访问记录:{request.method} url:{request.url}\nheaders:{request.headers}\nIP:{request.client.host}")

        response = await call_next(request)

        return response


def register_redis(app: FastAPI) -> None:
    """
    把redis挂载到app对象上面
    :param app:
    :return:
    """

    @app.on_event('startup')
    async def startup_event():
        """
        获取链接
        :return:
        """
        # aioredis 1.5
        # app.state.redis = await create_redis_pool(settings.REDIS_URL)
        # aioredis 2.0
        app.state.redis = aioredis.from_url(settings.REDIS_URL, encodings='utf-8', decode_responses=True)
        pass

    @app.on_event('shutdown')
    async def shutdown_event():
        """
        关闭
        :return:
        """
        app.state.redis.close()
        await app.state.redis.wait_closed()
