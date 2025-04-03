import datetime
from decimal import Decimal
from functools import partial
from typing import Any, Callable, Union

from fastapi.responses import ORJSONResponse
from orjson import orjson


class CustomORJSONResponse(ORJSONResponse):
    SERIALIZER_OPTIONS = (
            orjson.OPT_SERIALIZE_NUMPY |
            orjson.OPT_SERIALIZE_UUID |
            orjson.OPT_NAIVE_UTC |
            orjson.OPT_UTC_Z |
            orjson.OPT_OMIT_MICROSECONDS
    )

    def render(self, content: Any) -> bytes:

        def custom_serializer(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: custom_serializer(v) for k, v in obj.items()}

            if isinstance(obj, (list, tuple, set, frozenset)):
                return [custom_serializer(i) for i in obj]

            if isinstance(obj, datetime.datetime):
                if obj.tzinfo is None:
                    obj = obj.replace(tzinfo=datetime.timezone.utc)
                return obj.isoformat().replace("+00:00", "Z")

            if isinstance(obj, Decimal):
                return float(obj) if obj.as_tuple().exponent >= -6 else str(obj)  # 避免浮点数精度丢失

            if isinstance(obj, int) and abs(obj) >= 2 ** 53:
                return str(obj)

            if isinstance(obj, bytes):
                return obj.decode("utf-8", "ignore")  # 转换为字符串

            if isinstance(obj, datetime.timedelta):
                return obj.total_seconds()

            return obj

        try:
            content = custom_serializer(content)
            return orjson.dumps(
                content,
                option=self.SERIALIZER_OPTIONS,
                default=custom_serializer,
            )
        except Exception as e:
            raise ValueError(f"CustomORJSONResponse serializer fail: {e}") from e


class ResponseFactory:
    """
    # 使用示例
    factory = ResponseFactory()

    # 1. 使用预定义响应
    success_resp = factory.get(ResponseFactory.SUCCESS)(data={"id": 1})

    # 2. 注册自定义响应
    @factory.register(code=40003, default_message="Forbidden")
    def forbidden(*, code: int, message: str):
        return ResponseFactory._base_response(code=code, message=message)

    # 3. 使用自定义响应
    forbidden_resp = factory.get(40003)(message="No permission")
    """

    _instance = None

    # 标准状态码
    SUCCESS: int = 20000

    BadRequest: int = 40000
    Unauthorized: int = 40001
    NotFound: int = 40004
    Forbidden: int = 40003

    InternalServerError: int = 50000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_mapping()
        return cls._instance

    def _init_mapping(self):
        """初始化默认映射"""
        self._mapping = {
            self.SUCCESS: self.resp_200,
            200: self.resp_200,

            self.BadRequest: self.resp_401,
            401: self.resp_401,
            self.Unauthorized: self.resp_400,
            400: self.resp_400,
            self.NotFound: self.resp_404,
            404: self.resp_404,
            self.Forbidden: self.resp_403,

            self.InternalServerError: self.resp_500,
            500: self.resp_500
        }

    @staticmethod
    def _base_response(
            *,
            code: int = 200,
            data: Any = None,
            message: Union[list, dict, str] = ""
    ) -> ORJSONResponse:
        """基础响应构造器"""
        return CustomORJSONResponse(
            status_code=200,
            content={
                "code": code,
                "message": message,
                "data": data,
            }
        )

    # 预定义标准响应
    def resp_200(self, *, data: Any = None, message: str = "") -> ORJSONResponse:
        return self._base_response(code=self.SUCCESS, data=data, message=message)

    def resp_list(self, *, data: list, page: int, limit: int, total: int):
        return self.resp_200(data={"item": data, "page": page, "limit": limit, "total": total})

    def resp_400(self, *, data: Any = None, message: str = "") -> ORJSONResponse:
        message = f"Bad Request, {message}" if message else "Bad Request"
        return self._base_response(code=self.BadRequest, data=data, message=message)

    def resp_401(self, *, data: Any = None, message: str = "") -> ORJSONResponse:
        message = f"Unauthorized, {message}" if message else "Unauthorized"
        return self._base_response(code=self.Unauthorized, data=data, message=message)

    def resp_403(self, *, data: Any = None, message: str = "Forbidden") -> ORJSONResponse:
        message = f"Forbidden, {message}" if message else "Forbidden"
        return self._base_response(code=self.Forbidden, data=data, message=message)

    def resp_404(self, *, data: Any = None, message: str = "Not Found") -> ORJSONResponse:
        message = f"Not Found, {message}" if message else "Not Found"
        return self._base_response(code=self.NotFound, data=data, message=message)

    def resp_500(self, *, data: Any = None, message: str = "") -> ORJSONResponse:
        message = f"Internal Server Error, {message}" if message else "Internal Server Error"
        return self._base_response(code=self.InternalServerError, data=data, message=message)

    def response(self, *, code: int, data: Any = None, message: str = "") -> Callable:
        """获取响应构造器"""
        if code not in self._mapping:
            raise ValueError(f"Unregistered response code: {code}")
        response_func = self._mapping[code]
        return response_func(data=data, message=message)

    def register(self, code: int, *, default_message: str = ""):
        """注册新的响应类型（装饰器）"""

        def decorator(f):
            self._mapping[code] = partial(f, code=code, message=default_message)
            return f

        return decorator


# 使用示例
response_factory = ResponseFactory()
