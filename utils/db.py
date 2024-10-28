from contextlib import asynccontextmanager

# import aioredis
# from aioredis import Redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from core.config import setting
from utils import json_dumps, json_loads

# 创建 SQLAlchemy 基类
Base = declarative_base()

# 创建异步引擎
engine = create_async_engine(
    setting.sqlalchemy_database_uri,
    echo=setting.sqlalchemy_echo,
    pool_pre_ping=True,
    json_serializer=json_dumps,
    json_deserializer=json_loads
)

# 创建异步 session_maker
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# 创建依赖：每次请求使用一个数据库会话
@asynccontextmanager
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # Check if a transaction is active before rolling back
            if session.is_active:
                await session.rollback()
            raise
        finally:
            await session.close()


# Redis 依赖注入函数，用于在每个请求中获取 Redis 连接
# @asynccontextmanager
# async def get_redis() -> Redis:
#     async with aioredis.ConnectionPool.from_url(setting.redis_url, encoding="utf-8", decode_responses=True) as redis:
#         try:
#             yield redis
#         except Exception:
#             raise
#         finally:
#             await redis.close()
