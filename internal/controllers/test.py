import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
import numpy as np

from internal.utils.asyncio_task import async_task_manager
from pkg.logger import Logger
from pkg.resp import response_factory

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/test_raise_exception")
async def test_raise_exception(_: Request):
    # 如果触发fastapi.HTTPException会有限被main.py的exception_handler捕获，
    # 如果是Exception会被middleware的exception.py捕获
    raise HTTPException(500, "test_raise_exception")


@router.get("/test_custom_response_class_basic_types")
async def test_custom_response_class_basic_types(_: Request):
    return response_factory.resp_200(data={
        "large_int": 2 ** 53 + 1,  # 超过JS安全整数
        "normal_int": 42,
        "float_num": 3.1415926535,
        "boolean": True,
        "none_value": None,
    })


@router.get("/test_custom_response_class_containers")
async def test_custom_response_class_containers(_: Request):
    return response_factory.resp_200(data=[
        {"set_data": {1, 2, 3}},  # 集合转列表
        (4, 5, 6),  # 元组转列表
        [datetime(2023, 1, 1), datetime(2023, 1, 1, tzinfo=timezone.utc)]
    ])


@router.get("/test_custom_response_class_nested")
async def test_custom_response_class_nested(_: Request):
    return response_factory.resp_200(data={
        "level1": {
            "level2": [
                {
                    "mixed_types": [
                        Decimal("999.999"),
                        {uuid.uuid4(): datetime.now()},
                        [2 ** 60, {"deep": True}]
                    ]
                }
            ]
        }
    })


@router.get("/test_custom_response_class_third_party")
async def test_custom_response_class_third_party(_: Request):
    return response_factory.resp_200(data={
        "numpy_array": np.array([1.1, 2.2, 3.3]),  # NumPy数组
        "numpy_int": np.int64(2 ** 63 - 1)
    })


@router.get("/test_custom_response_class_edge_cases")
async def test_custom_response_class_edge_cases(_: Request):
    return response_factory.resp_200(data={
        "numpy_array": np.array([1.1, 2.2, 3.3]),  # NumPy数组
        "numpy_int": np.int64(2 ** 63)
    })


@router.get("/test_custom_response_class_edge_cases")
async def test_custom_response_class_complex(_: Request):
    return response_factory.resp_200(data={
        "empty_dict": {},
        "empty_list": [],
        "zero": Decimal("0.000000"),
        "max_precision": Decimal("0.12345678901234567890123456789")
    })


@router.get("/test_custom_response_class_special_types")
async def test_custom_response_class_special_types(_: Request):
    return response_factory.resp_200(data={
        "decimal": Decimal("123.4567890123456789"),
        "bytes": b"\x80abc\xff",
        "datetime_naive": datetime.now(),
        "big_int": 2 ** 60,
        "timedelta": timedelta(days=1, seconds=3600)
    })


async def async_task():
    """可以继承上下文的trace_id"""
    Logger.info("async_task, trace_id-test")
    await asyncio.sleep(10)


@router.get("/test_contextvars_on_asyncio_task")
async def test_contextvars_on_asyncio_task():
    await  async_task_manager.add_task("test", async_task)
    return response_factory.resp_200()
