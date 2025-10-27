"""该目录重要用于定义各种schema"""
from datetime import datetime
from typing import Any
from pydantic import GetCoreSchemaHandler
from pydantic_core.core_schema import CoreSchema, no_info_plain_validator_function
from pydantic.json_schema import JsonSchemaValue


class IntStr(int):
    """前端传字符串，后端当整数用"""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: Any) -> JsonSchemaValue:
        # 告诉 FastAPI 这个字段在文档中是整数类型
        return {"type": "integer", "example": 123}

    @classmethod
    def validate(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        raise ValueError("Must be an integer or numeric string")


class UtcDatetimeStr(datetime):
    """将前端 ISO 格式的 UTC 时间字符串转为无时区 datetime"""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: Any) -> JsonSchemaValue:
        return {
            "type": "string",
            "format": "date-time",
            "example": "2025-05-07T14:30:00Z"
        }

    @classmethod
    def validate(cls, v: Any) -> datetime:
        if isinstance(v, datetime):
            return v.replace(tzinfo=None)  # 去掉时区
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt.replace(tzinfo=None)  # 去掉时区信息
            except ValueError:
                raise ValueError("Must be a valid ISO 8601 datetime string")
        raise ValueError("Must be a datetime or ISO datetime string")