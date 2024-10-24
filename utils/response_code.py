from decimal import Decimal

from fastapi import status
from fastapi.responses import JSONResponse, ORJSONResponse

from typing import Union

from orjson import orjson


# 自定义响应类，预处理数据中的 Decimal 类型
class CustomORJSONResponse(ORJSONResponse):
    def render(self, content: any) -> bytes:
        assert orjson is not None, "orjson must be installed to use ORJSONResponse"

        # 遍历数据，将所有 Decimal 转换为 float
        def default_serializer(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

        # 使用 orjson.dumps 序列化数据，自动转换 Decimal 类型
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
                            default=default_serializer)


def resp_200(*, data: Union[list, dict, str] = None, message: str = "success"):
    return CustomORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'code': 200,
            'message': message,
            'data': data,
        },
    )


def resp_400(*, data: str = None, message: str = "BAD REQUEST") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            'code': 400,
            'message': message,
            'data': data,
        }
    )


def resp_403(*, data: str = None, message: str = "Forbidden") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            'code': 403,
            'message': message,
            'data': data,
        }
    )


def resp_404(*, data: str = None, message: str = "Page Not Found") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            'code': 404,
            'message': message,
            'data': data,
        }
    )


def resp_422(*, data: str = None, message: Union[list, dict, str] = "UNPROCESSABLE_ENTITY") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            'code': 422,
            'message': message,
            'data': data,
        }
    )


def resp_500(*, data: str = None, message: Union[list, dict, str] = "Server Internal Error") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            'code': "500",
            'message': message,
            'data': data,
        }
    )


# 自定义
def resp_5000(*, data: Union[list, dict, str] = None, message: str = "Token failure") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'code': 5000,
            'message': message,
            'data': data,
        }
    )


def resp_5001(*, data: Union[list, dict, str] = None, message: str = "User Not Found") -> JSONResponse:
    return CustomORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'code': 5001,
            'message': message,
            'data': data,
        }
    )
