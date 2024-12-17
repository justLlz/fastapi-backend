from typing import Optional, Any

from fastapi import HTTPException, status
from loguru import logger
from orjson import JSONDecodeError

from pkg import create_uuid_session, json_dumps, json_loads, session_cache_key, session_list_cache_key
from internal.infra.db import get_redis


async def set_session(session: str, user_data: dict, ex: Optional[int] = 10800):
    """
    设置会话键值，并设置过期时间。
    """
    key = session_cache_key(session)
    value = json_dumps(user_data)
    await set_value(key, value, ex)


async def get_session_value(session: str) -> dict:
    """
    获取会话中的用户ID和用户类型。
    """
    return await get_value(session_cache_key(session))


async def set_session_list(user_id: int, session: str):
    cache_key = session_list_cache_key(user_id)
    session_list = await get_list(cache_key)
    length_session_list = len(session_list)
    try:
        async with get_redis() as redis:
            if not session_list or length_session_list < 3:
                await redis.rpush(cache_key, session)
            else:
                if len(session_list) >= 3:
                    old_session = await redis.lpop(cache_key)
                    # 删除旧的session
                    # await redis.delete(session_cache_key(old_session))
                    # 插入新的session
                    await redis.rpush(cache_key, session)
                    logger.warning(
                        f"Session list for user {user_id} is full, popping and deleting oldest session: {old_session}")
    except Exception as e:
        logger.error(f"Failed to pop ande delete value from list {cache_key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 设置键值对
async def set_value(key: str, value: Any, ex: Optional[int] = None) -> bool:
    """
    设置键值对并可选设置过期时间。
    """
    try:
        async with get_redis() as redis:
            return await redis.set(key, value, ex=ex)
    except Exception as e:
        logger.error(f"Failed to set key {key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取键值
async def get_value(key: str) -> Optional[dict | Any]:
    """
    获取键值。
    """
    try:
        async with get_redis() as redis:
            value = await redis.get(key)
            if value is None:
                return None

            if isinstance(value, bytes):
                value = value.decode("utf-8")

            try:
                return json_loads(value)
            except JSONDecodeError as _:
                return value
    except Exception as e:
        logger.error(f"Failed to get key {key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 删除键
async def delete_key(key: str) -> int:
    """
    删除键。
    """
    try:
        async with get_redis() as redis:
            return await redis.delete(key)
    except Exception as e:
        logger.error(f"failed to delete key {key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 设置过期时间
async def set_expiry(key: str, ex: int) -> bool:
    """
    设置键的过期时间。
    """
    try:
        async with get_redis() as redis:
            return await redis.expire(key, ex)
    except Exception as e:
        logger.error(f"Failed to set expiry for key {key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 检查键是否存在
async def key_exists(key: str) -> bool:
    """
    检查键是否存在。
    """
    try:
        async with get_redis() as redis:
            return await redis.exists(key) > 0
    except Exception as e:
        logger.error(f"Failed to check existence of key {key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取键的剩余 TTL
async def get_ttl(key: str) -> int:
    """
    获取键的剩余生存时间。
    """
    try:
        async with get_redis() as redis:
            return await redis.ttl(key)
    except Exception as e:
        logger.error(f"Failed to get TTL for key {key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 添加到哈希表
async def set_hash(name: str, key: str, value: Any) -> bool:
    """
    在 Redis 哈希表中设置键值。
    """
    try:
        async with get_redis() as redis:
            return await redis.hset(name, key, value) > 0
    except Exception as e:
        logger.error(f"Failed to set hash {name}:{key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取哈希表中的值
async def get_hash(name: str, key: str) -> Optional[str]:
    """
    从 Redis 哈希表中获取值。
    """
    try:
        async with get_redis() as redis:
            value = await redis.hget(name, key)
            return value.decode() if value else None
    except Exception as e:
        logger.error(f"Failed to get hash {name}:{key}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 向列表添加值
async def push_to_list(name: str, value: Any, direction: str = "right") -> int:
    """
    向列表中添加值。
    """
    try:
        async with get_redis() as redis:
            if direction == "left":
                return await redis.lpush(name, value)
            else:
                return await redis.rpush(name, value)
    except Exception as e:
        logger.error(f"Failed to push value to list {name}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# 获取列表中的所有值
async def get_list(name: str) -> list[str]:
    """
    获取列表中的所有值。
    """
    try:
        async with get_redis() as redis:
            values = await redis.lrange(name, 0, -1)
            return values
    except Exception as e:
        logger.error(f"Failed to get list {name}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def left_pop_list(name: str) -> Optional[str]:
    """
    从列表左侧弹出一个值。
    """
    try:
        async with get_redis() as redis:
            value = await redis.lpop(name)
            return value.decode() if value else None
    except Exception as e:
        logger.error(f"Failed to pop value from list {name}: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def login_and_set_session(user_data: dict) -> str:
    session = create_uuid_session()
    user_id = user_data["id"]

    await set_session(session, user_data)
    await set_session_list(user_id, session)
    return session
