import asyncio
import random
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
from fastapi import APIRouter, HTTPException, Request

from internal.models.user import User
from internal.utils.asyncio_task import async_task_manager
from internal.utils.orm_helpers import new_cls_querier, new_cls_updater, new_counter
from pkg.logger_helper import logger
from pkg.resp_helper import response_factory

router = APIRouter(prefix="/test", tags=["public v1 test"])


@router.get("/test_raise_exception")
async def test_raise_exception(_: Request):
    # 如果触发fastapi.HTTPException会有限被main.py的exception_handler捕获，
    # 如果是Exception会被middleware的exception.py捕获
    raise Exception("test_raise_exception")


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
    logger.info(f"async_task_trace_id-test")
    await asyncio.sleep(10)


@router.get("/test_contextvars_on_asyncio_task")
async def test_contextvars_on_asyncio_task():
    await  async_task_manager.add_task("test", async_task)
    return response_factory.resp_200()


@router.get("/test_dao")
async def test_dao():
    unique_hex = uuid.uuid4().hex[:16]  # 缩短长度
    test_user = User.init_by_phone(str(random.randint(10000000000, 99999999999)))
    test_user.account = f"lilinze_{unique_hex}"
    test_user.username = f"lilinze_{unique_hex}"
    await test_user.save()

    try:
        # 1. 验证基础查询
        created_user = await new_cls_querier(User).eq(User.id, test_user.id).get_or_exec()
        assert created_user.id == test_user.id
        logger.info(f"test created success")

        # 2. 测试各种查询操作符
        # eq
        user = await new_cls_querier(User).eq(User.id, test_user.id).get_or_none()
        assert user.id == test_user.id
        logger.info(f"test eq success")

        # ne
        ne_users = await new_cls_querier(User).ne(User.id, test_user.id).all()
        assert all(u.id != test_user.id for u in ne_users)
        logger.info(f"test ne success")

        # gt
        gt_users = await new_cls_querier(User).gt(User.id, test_user.id).all()
        assert all(u.id > test_user.id for u in gt_users)
        logger.info(f"test gt success")

        # lt
        lt_users = await new_cls_querier(User).lt(User.id, test_user.id).all()
        assert all(u.id < test_user.id for u in lt_users)
        logger.info(f"test lt success")

        # ge
        ge_users = await new_cls_querier(User).ge(User.id, test_user.id).all()
        assert all(u.id >= test_user.id for u in ge_users)
        logger.info(f"test ge success")

        # le
        le_users = await new_cls_querier(User).le(User.id, test_user.id).all()
        assert all(u.id <= test_user.id for u in le_users)
        logger.info(f"test le success")

        # in_ 测试
        in_users = await new_cls_querier(User).in_(User.id, [test_user.id]).all()
        assert len(in_users) == 1
        logger.info(f"test in_ success")

        # like 测试
        like_users = await new_cls_querier(User).like(User.username, "lilinze").all()
        assert all("lilinze" in u.username for u in like_users)
        logger.info(f"test like success")

        # is_null 测试（确保测试时deleted_at为null）
        null_users = await new_cls_querier(User).is_null(User.deleted_at).all()
        assert any(u.deleted_at is None for u in null_users)
        logger.info(f"test is_null success")

        # 4. 计数测试
        count = await new_counter(User).ge(User.id, 0).count()
        assert count >= 1
        logger.info(f"test count success")

        # AND 组合
        and_users = await (new_cls_querier(User).
                           eq(User.username, test_user.username).
                           eq(User.account, test_user.account).get_or_exec())
        assert and_users.username == test_user.username, and_users.account == test_user.account
        logger.info(f"test and success")

        # where 组合
        where_user = await new_cls_querier(User).where(
            User.username == test_user.username,
            User.account == test_user.account
        ).get_or_exec()
        assert where_user.username == test_user.username, where_user.account == test_user.account
        logger.info(f"test where success")

        # where_by 组合
        where_by_query_dict = {"username": test_user.username, "account": test_user.account}
        where_by_users = await new_cls_querier(User).where_by(
            **where_by_query_dict
        ).get_or_exec()
        assert where_by_users.username == test_user.username, where_by_users.account == test_user.account
        logger.info(f"test where_by success")

        # OR 组合
        or_users = await new_cls_querier(User).or_(
            User.username == test_user.username,
            User.account == "invalid_account"
        ).all()
        assert len(or_users) >= 1
        logger.info(f"test or success")

        # BETWEEN 组合
        between_users = await new_cls_querier(User).between(
            User.id,
            (test_user.id - 1, test_user.id + 1)
        ).all()
        assert len(between_users) >= 1
        logger.info(f"test between success")

        # 3. 更新操作测试
        # 显式使用新查询器避免缓存问题
        updated_name = f"updated_name_{unique_hex}"
        await new_cls_updater(model_cls=User).eq(User.id, test_user.id).update(username=updated_name).execute()
        # 重新查询验证更新
        updated_user = await new_cls_querier(User).eq(User.id, test_user.id).get_or_exec()
        assert updated_user.username == updated_name
        logger.info(f"test update-1 success")

        # 显式使用新查询器避免缓存问题
        updated_name = f"updated_name_{unique_hex}"
        await new_cls_updater(model_cls=User).eq(User.id, test_user.id).update(
            **{"username": updated_name}).execute()
        # 重新查询验证更新
        updated_user = await new_cls_querier(User).eq(User.id, test_user.id).get_or_exec()
        assert updated_user.username == updated_name
        logger.info(f"test update-2 success")
    except Exception as e:
        logger.error(f"test dao error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        return response_factory.resp_200()
    finally:
        test_user.deleted_at = datetime.now()
        await test_user.save()

