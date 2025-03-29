import datetime
from decimal import Decimal
from typing import Any, Union

from fastapi.responses import ORJSONResponse
from orjson import orjson
from starlette.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN,
                              HTTP_404_NOT_FOUND, HTTP_413_REQUEST_ENTITY_TOO_LARGE, HTTP_422_UNPROCESSABLE_ENTITY,
                              HTTP_500_INTERNAL_SERVER_ERROR)


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


# 通用响应函数，用于避免重复代码
def custom_response(
        *,
        status_code: int = HTTP_200_OK,
        code: str = '',
        message: Union[str, list, dict] = "success",
        data: Union[list, dict, str, None] = None
) -> CustomORJSONResponse:
    """通用响应生成器，减少重复"""
    return CustomORJSONResponse(
        status_code=status_code,
        content={
            'code': code,
            'message': message,
            'data': data,
        }
    )


def resp_failed(code: int, message: str) -> CustomORJSONResponse:
    return custom_response(
        status_code=200,
        code=str(code),
        message=message,
        data=None
    )


def resp_success(*, data: Union[list, dict, str] = None):
    return custom_response(
        status_code=200,
        code='200',
        message='success',
        data=data
    )


# 各种状态码的响应函数
def resp_200(*, data: Union[list, dict, str] = None):
    return resp_success(data=data)


def resp_400(*, message: str = "BAD REQUEST"):
    return resp_failed(HTTP_400_BAD_REQUEST, message=message)


def resp_401(*, message: str = "UNAUTHORIZED"):
    return resp_failed(code=HTTP_401_UNAUTHORIZED, message=message)


def resp_403(*, message: str = "Forbidden"):
    return resp_failed(HTTP_403_FORBIDDEN, message=message)


def resp_404(*, message: str = "Not Found"):
    return resp_failed(code=HTTP_404_NOT_FOUND, message=message)


def resp_422(*, message: Union[list, dict, str] = "UNPROCESSABLE_ENTITY"):
    return resp_failed(code=HTTP_422_UNPROCESSABLE_ENTITY, message=message)


def resp_413(*, message: Union[list, dict, str] = "Payload Too Large"):
    return resp_failed(code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, message=message)


def resp_500(*, message: Union[list, dict, str] = "Server Internal Error"):
    return resp_failed(HTTP_500_INTERNAL_SERVER_ERROR, message=message)


# 自定义错误码的响应
def resp_5000(*, message: str = "Token failure"):
    return resp_failed(code=5000, message=message)


def resp_5001(*, message: str = "User Not Found"):
    return resp_failed(code=5001, message=message)
