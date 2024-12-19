import datetime
from decimal import Decimal
from fastapi.responses import ORJSONResponse
from typing import Any, Union
from orjson import orjson
from starlette.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN,
                              HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                              HTTP_500_INTERNAL_SERVER_ERROR)


class CustomORJSONResponse(ORJSONResponse):
    def render(self, content: Any) -> bytes:
        def convert_value(obj: Any) -> Any:
            match obj:
                case dict():
                    return {k: convert_value(v) for k, v in obj.items()}
                case list():
                    return [convert_value(i) for i in obj]
                case datetime.datetime() as dt:
                    # 将 datetime 类型转换为 ISO 格式字符串，并标记为 UTC 时间
                    str_value = dt.isoformat()
                    return str_value + "Z" if dt.tzinfo is None else str_value
                case Decimal() as dec:
                    return float(dec)
                case int() as i if abs(i) >= 10 ** 15:
                    # 超长整数转换为字符串
                    return str(i)
                case _:
                    return obj

        # 转换内容中的特定数据类型
        content = convert_value(content)

        # 使用 orjson.dumps 序列化数据
        return orjson.dumps(
            content,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
        )


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


def resp_success(*, data: Union[list, dict, str]):
    return custom_response(
        status_code=200,
        code='200',
        message='success',
        data=data
    )


# 各种状态码的响应函数
def resp_200(*, data: Union[list, dict, str] = None, message: str = "success"):
    return custom_response(status_code=HTTP_200_OK, code='200', message=message, data=data)


def resp_400(*, message: str = "BAD REQUEST"):
    return custom_response(status_code=HTTP_400_BAD_REQUEST, code='400', message=message)


def resp_401(*, message: str = "UNAUTHORIZED"):
    return custom_response(status_code=HTTP_401_UNAUTHORIZED, code='401', message=message)


def resp_403(*, message: str = "Forbidden"):
    return custom_response(status_code=HTTP_403_FORBIDDEN, code='403', message=message)


def resp_404(*, message: str = "Not Found"):
    return custom_response(status_code=HTTP_404_NOT_FOUND, code='404', message=message)


def resp_422(*, message: Union[list, dict, str] = "UNPROCESSABLE_ENTITY"):
    return custom_response(status_code=HTTP_422_UNPROCESSABLE_ENTITY, code='422', message=message)


def resp_413(*, message: Union[list, dict, str] = "Payload Too Large"):
    return custom_response(status_code=HTTP_413_REQUEST_ENTITY_TOO_LARGE, code='413', message=message)


def resp_500(*, message: Union[list, dict, str] = "Server Internal Error"):
    return custom_response(status_code=HTTP_500_INTERNAL_SERVER_ERROR, code='500', message=message)


# 自定义错误码的响应
def resp_5000(*, message: str = "Token failure"):
    return resp_failed(code=5000, message=message)


def resp_5001(*, message: str = "User Not Found"):
    return resp_failed(code=5001, message=message)
