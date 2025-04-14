"""该目录重要用于定义各种schema"""

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
