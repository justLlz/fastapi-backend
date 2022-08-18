from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from settings import setting
from utils.common import json_dumps, json_loads

# 创建对象的基类:
Base = declarative_base()

# 初始化数据库连接:
engine = create_engine(setting.SQLALCHEMY_DATABASE_URI, echo=setting.SQLALCHEMY_ECHO, pool_pre_ping=True,
                       json_serializer=json_dumps, json_deserializer=json_loads)

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_local():
    return SessionLocal()
