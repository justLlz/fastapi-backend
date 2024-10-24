from typing import Union

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, BigInteger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core.db import Base, get_session
from utils import int_utc_timestamp
from utils.custom_exc import GlobalException
from utils.logger import logger


class ModelMixin(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=int_utc_timestamp())
    updated_at = Column(DateTime, default=int_utc_timestamp(), onupdate=int_utc_timestamp())

    @classmethod
    async def get(cls, record_id: int):
        async with get_session() as session:
            try:
                return session.query(cls).get(record_id)
            except Exception as e:
                logger.error(f'{cls.__name__}-db save err: {e}')

    async def save(self):
        async with get_session() as session:
            try:
                session.add(self)  # 将当前实例添加到会话
                await session.commit()  # 提交更改
                await session.refresh(self)  # 刷新实例以获取数据库中更新后的数据
            except Exception as e:
                raise GlobalException(f'{self.__class__.__name__}-db save err: {e}')

    async def delete(self):
        async with get_session() as session:
            try:
                session.delete(self)
                session.commit()
            except Exception as e:
                raise GlobalException(f'{self.__class__.__name__}-db delete err: {e}')

    @classmethod
    def create(cls, data: Union[dict, BaseModel]):
        # 创建一个新实例
        instance = cls()

        # 如果是 Pydantic 模型，则转为字典
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)

        # 使用 data 字典填充实例字段
        instance._populate(data)
        return instance

    def update(self, update_record: BaseModel):
        # 从 Pydantic 模型中提取更新数据
        update_data = update_record.model_dump(exclude_unset=True)

        # 更新当前实例字段
        self._populate(update_data)

    def _populate(self, data: dict):
        # 遍历字段并更新当前实例
        cols = self.__class__.__table__.columns.keys()
        for col in cols:
            if col in data:
                setattr(self, col, data[col])
