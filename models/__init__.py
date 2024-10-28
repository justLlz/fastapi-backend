from typing import Union
from fastapi import status, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, BigInteger, select

from utils.db import Base, get_session
from utils import int_utc_timestamp


class ModelMixin(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=int_utc_timestamp())
    updated_at = Column(DateTime, default=int_utc_timestamp(), onupdate=int_utc_timestamp())

    @classmethod
    async def get(cls, record_id: int):
        async with get_session() as session:
            try:
                stmt = select(cls).where(cls.id == record_id)
                result = await session.execute(stmt)
                data = result.scalars().first()
                if not data:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{cls.__name__} not found")
                return data
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{cls.__name__} database error: {e}')

    async def save(self):
        async with get_session() as session:
            try:
                session.add(self)
                await session.commit()
            except Exception as e:
                # await session.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.__class__.__name__} save error: {e}')

    async def delete(self):
        async with get_session() as session:
            try:
                await session.delete(self)
                await session.commit()
            except Exception as e:
                # await session.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.__class__.__name__} delete error: {e}')

    @classmethod
    def create(cls, data: Union[dict, BaseModel]):
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)
        # 创建并返回填充好的实例
        return cls(**data)

    def update(self, update_record: BaseModel):
        update_data = update_record.model_dump(exclude_unset=True)
        self._populate(update_data)

    def _populate(self, data: dict):
        # 遍历字段并更新当前实例
        cols = self.__class__.__table__.columns.keys()
        for col, value in data.items():
            if col in cols:
                setattr(self, col, value)
