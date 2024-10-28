from decimal import Decimal
from fastapi import status
from fastapi.responses import ORJSONResponse
from typing import Any, Union
from orjson import orjson


# 自定义响应类，预处理数据中的 Decimal 类型
class CustomORJSONResponse(ORJSONResponse):
    def render(self, content: Any) -> bytes:
        def default_serializer(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        # 使用 orjson.dumps 序列化数据，自动转换 Decimal 类型
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
                            default=default_serializer)


# 通用响应函数，用于避免重复代码
def custom_response(
    *,
    status_code: int = status.HTTP_200_OK,
    code: int,
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


# 各种状态码的响应函数
def resp_200(*, data: Union[list, dict, str] = None, message: str = "success"):
    return custom_response(status_code=status.HTTP_200_OK, code=200, message=message, data=data)


def resp_400(*, data: str = None, message: str = "BAD REQUEST"):
    return custom_response(status_code=status.HTTP_400_BAD_REQUEST, code=400, message=message, data=data)


def resp_403(*, data: str = None, message: str = "Forbidden"):
    return custom_response(status_code=status.HTTP_403_FORBIDDEN, code=403, message=message, data=data)


def resp_404(*, data: str = None, message: str = "Page Not Found"):
    return custom_response(status_code=status.HTTP_404_NOT_FOUND, code=404, message=message, data=data)


def resp_422(*, data: str = None, message: Union[list, dict, str] = "UNPROCESSABLE_ENTITY"):
    return custom_response(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, code=422, message=message, data=data)


def resp_500(*, data: str = None, message: Union[list, dict, str] = "Server Internal Error"):
    return custom_response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code=500, message=message, data=data)


# 自定义错误码的响应
def resp_5000(*, data: Union[list, dict, str] = None, message: str = "Token failure"):
    return custom_response(code=5000, message=message, data=data)


def resp_5001(*, data: Union[list, dict, str] = None, message: str = "User Not Found"):
    return custom_response(code=5001, message=message, data=data)