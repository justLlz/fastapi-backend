import datetime
import hashlib
import os
import re
import string
import time
import random
import uuid
from typing import List, Optional

import colorama
import orjson
import pytz
import shortuuid
import xxhash


def json_dumps(*args, **kwargs):
    return orjson.dumps(*args, **kwargs).decode("utf-8")


def json_loads(*args, **kwargs):
    return orjson.loads(*args, **kwargs)


def datetime_to_string(val: datetime.datetime) -> str:
    """
    格式化 datetime 对象为字符串。
    - 如果有时区信息，保留时区信息并使用 ISO 格式。
    - 如果没有时区信息，假定为 UTC，并格式化为 '2024-12-06T14:12:31Z' 格式。

    Args:
        val (datetime): 要格式化的 datetime 对象。

    Returns:
        str: 格式化后的字符串。
    """
    if val.tzinfo:
        # 有时区信息，保留时区信息并使用 ISO 格式
        return val.isoformat()
    else:
        # 没有时区信息，添加 'Z' 表示 UTC 时间
        return val.replace(tzinfo=pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def convert_to_utc(val: datetime) -> datetime.datetime:
    """
    将没有时区信息的东八区时间转换为 UTC 时间

    Args:
        val (datetime): 要转换的 datetime 对象。

    Returns:
        datetime: 转换后的 UTC 时间，且不带时区信息。
    """
    # 如果没有时区信息，假定为东八区时间
    if val.tzinfo is None:
        val = pytz.timezone('Asia/Shanghai').localize(val)

    # 转换为 UTC 时间并移除时区信息
    return val.astimezone(pytz.utc)


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


def get_utc_datetime() -> datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def get_sys_env_var() -> str:
    return str.lower(os.getenv("FAST_API_ENV", ""))


# 把"2024-10-21T12:26:04+08:00"转化成utcdatetime
def parse_datetime_from_str(s: str) -> Optional[datetime]:
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

    if not (isinstance(d1, dict) and isinstance(d2, dict)):
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


def session_cache_key(session: str) -> str:
    return f"session:{session}"


def session_list_cache_key(user_id: int) -> str:
    return f"session_list:{user_id}"


# 生成唯一的文件名
def generate_unique_filename(filename: str) -> str:
    return f"{uuid.uuid4().hex}_{filename}"


def create_uuid_session():
    return shortuuid.uuid()


def validate_phone_number(phone: str) -> bool:
    """
    校验手机号是否符合中国大陆的手机号格式
    :param phone: 待验证的手机号字符串
    :return: 如果手机号格式正确，返回 True，否则返回 False
    """
    # 正则表达式：以1开头，第二位是3-9之间的数字，后面是9个数字
    pattern = r"^1[3-9]\d{9}$"

    if re.match(pattern, phone):
        return True
    else:
        return False


def generate_account_by_phone(phone_number: str) -> str:
    # 选择哈希算法（例如 SHA-256）
    hashed_phone = hashlib.sha256(phone_number.encode('utf-8')).hexdigest()

    # 为了增加唯一性，也可以使用 UUID 来保证生成的 ID 是唯一的
    unique_account_id = f"user_{hashed_phone}"

    return unique_account_id


class ColorPrint:
    colorama.init(autoreset=True)

    @staticmethod
    def red(text):
        print(colorama.Fore.RED + text)

    @staticmethod
    def green(text):
        print(colorama.Fore.GREEN + text)

    @staticmethod
    def yellow(text):
        print(colorama.Fore.YELLOW + text)

    @staticmethod
    def blue(text):
        print(colorama.Fore.BLUE + text)


colorprint = ColorPrint()
