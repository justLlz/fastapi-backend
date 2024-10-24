from contextlib import asynccontextmanager

# import aioredis
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from core.config import setting
from utils import json_dumps, json_loads

# 创建对象的基类:
Base = declarative_base()

# 创建异步引擎
engine = create_async_engine(setting.SQLALCHEMY_DATABASE_URI, echo=setting.SQLALCHEMY_ECHO, pool_pre_ping=True,
                             json_serializer=json_dumps, json_deserializer=json_loads)

# 创建异步 session_maker
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# 创建依赖：每次请求使用一个数据库会话
@asynccontextmanager
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()  # 确保会话在使用后正确关闭


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = None  # 初始化 redis 为 None 以确保 finally 中不出错
    try:
        # 创建 Redis 连接
        # app.state.redis = await aioredis.from_url(setting.REDIS_URL, encoding='utf-8', decode_responses=True)
        print("Redis connection established")
        yield
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
    finally:
        # 关闭 Redis 连接
        # if app.state.redis:  # 确保 redis 连接存在才调用 close
        #     await app.state.redis.close()
        print("Redis connection closed")


# 依赖注入函数，用于在每个请求中获取 Redis 连接
async def get_redis(app: FastAPI):
    return app.state.redis
