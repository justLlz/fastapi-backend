import datetime
import os
import string
import time
import random
from typing import List, Optional

import orjson
import xxhash


def json_dumps(*args, **kwargs):
    return orjson.dumps(*args, **kwargs).decode("utf-8")


def json_loads(*args, **kwargs):
    return orjson.loads(*args, **kwargs)


def hash_to_int(data: str) -> int:
    return xxhash.xxh64_intdigest(data)


def extract_dict(d, keys):
    return {k: v for k, v in d.items() if k in keys}


def ensure_list(v) -> List:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def get_utc_timestamp() -> int:
    return int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())


def get_utc_datetime() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def get_env_var() -> str:
    env_var = str.lower(os.getenv('FAST_API_ENV', 'dev'))
    return env_var


# 把"2024-10-21T12:26:04+08:00"转化成utcdatetime
def parse_datetime_from_str(s: str) -> Optional[datetime.datetime]:
    if not s or s == "0001-01-01T00:00:00Z":
        return None
    # 先把字符串转化成datetime
    dt = datetime.datetime.fromisoformat(s)
    # 再把datetime转化成utcdatetime
    return dt.astimezone(datetime.timezone.utc)


# 取两个列表不同的元素，比如[1, 2, 3], [3, 4, 5] => [1, 2, 4, 5]
def diff_list(a: List, b: List) -> List:
    return list(set(a).symmetric_difference(set(b)))


# 列表去重
def unique_iterable(v: list | tuple | set) -> list:
    match v:
        case list() | tuple():
            return list(dict.fromkeys(v))
        case set():
            return list(v)
        case _:
            raise ValueError("a must be list, tuple or set")


# 合并列表
def merge_list(a: List, b: List) -> List:
    return list(set(a).union(set(b)))


def unique_string_w_timestamp() -> str:
    """
    使用时间戳和随机数生成唯一字符串。
    """
    timestamp = str(int(time.time() * 1e6))  # 精确到微秒的时间戳
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return timestamp + random_part


def deep_compare_dict(d1, d2):
    if d1 is None and d2 is None:
        return True

    if d1 is None or d2 is None:
        return False

    if d1.keys() != d2.keys():
        return False
    for key in d1:
        if isinstance(d1[key], dict) and isinstance(d2[key], dict):
            if not deep_compare_dict(d1[key], d2[key]):
                return False
        elif d1[key] != d2[key]:
            return False
    return True
