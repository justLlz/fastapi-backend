from contextlib import asynccontextmanager
from typing import AsyncGenerator

from redis.asyncio import ConnectionPool, Redis
from sqlalchemy import Engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from internal.setting import setting
from pkg import json_dumps, json_loads
from pkg.logger import Logger

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
async def get_session() -> AsyncGenerator[AsyncSession]:
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


def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    try:
        compiled_statement = statement
        if parameters:
            compiled_statement = text(statement % tuple(parameters)).compile(compile_kwargs={"literal_binds": True})
        Logger.info(f"Executing SQL: {compiled_statement}")
    except Exception as e:
        Logger.error(f"Error while printing SQL: {e}")


# 监听 before_cursor_execute 事件，将事件处理函数绑定到 Engine 上
event.listen(Engine, "before_cursor_execute", before_cursor_execute)

# 创建全局的连接池实例
RedisConnectPool = ConnectionPool.from_url(setting.redis_url, encoding="utf-8", decode_responses=True)


@asynccontextmanager
async def get_redis() -> AsyncGenerator[Redis]:
    redis = Redis(connection_pool=RedisConnectPool)  # 使用连接池创建 Redis 客户端
    try:
        yield redis
    except Exception:
        raise
    finally:
        await redis.close()
