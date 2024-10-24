import datetime
import functools
import json
import logging
from typing import List

import orjson
import xxhash

import datetime
import json


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            print(obj.strftime('%Y-%m-%d %H:%M:%S'))
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return json.JSONEncoder.default(self, obj)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()

        if isinstance(obj, datetime.timedelta):
            return str(obj)

        super(JSONEncoder, self).default(obj)


def json_dumps(*args, **kwargs):
    return orjson.dumps(*args, **kwargs)


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


def int_utc_timestamp() -> int:
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp())
