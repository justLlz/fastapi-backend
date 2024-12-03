from contextlib import asynccontextmanager
from typing import Optional

from redis.asyncio import ConnectionPool, Redis

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import setting
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
async def get_local_session() -> AsyncSession:
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


# 创建异步引擎
design_gpt_engine = create_async_engine(
    setting.design_gpt_sqlalchemy_database_uri,
    echo=setting.design_gpt_sqlalchemy_echo,
    pool_pre_ping=True,
    json_serializer=json_dumps,
    json_deserializer=json_loads
)

# 创建异步 session_maker
DesignGptAsyncSessionLocal = async_sessionmaker(bind=design_gpt_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_design_gpt_session() -> AsyncSession:
    async with DesignGptAsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # Check if a transaction is active before rolling back
            if session.is_active:
                await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session(sess: Optional[AsyncSession] = None) -> AsyncSession:
    if sess:
        yield sess
    else:
        async with get_local_session() as session:
            yield session


# 创建全局的连接池实例
pool = ConnectionPool.from_url(setting.redis_url, encoding="utf-8", decode_responses=True)


@asynccontextmanager
async def get_redis() -> Redis:
    redis = Redis(connection_pool=pool)  # 使用连接池创建 Redis 客户端
    try:
        yield redis
    except Exception:
        raise
    finally:
        await redis.close()
