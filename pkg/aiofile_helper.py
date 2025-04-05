from typing import Any
from fastapi import HTTPException

import aiofiles
from loguru import logger
from orjson import orjson

from pkg import json_loads


async def read_json_file(file_path: str) -> Any:
    """
    异步读取 JSON 文件。

    参数:
        file_path (str): 要读取的 JSON 文件路径。

    返回:
        Any: 解析后的 JSON 数据。

    异常:
        FileNotFoundError: 如果文件不存在。
        json.JSONDecodeError: 如果文件内容不是有效的 JSON。
    """
    try:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            contents = await f.read()
            return json_loads(contents)
    except FileNotFoundError:
        logger.error(f"{file_path} not found")
        raise
    except orjson.JSONDecodeError as e:
        logger.error(f"invalid JSON in {file_path}: {repr(e)}")
        raise
    except Exception as e:
        logger.error(f"failed to read {file_path}: {repr(e)}")
        raise HTTPException(status_code=500, detail=str(e))
