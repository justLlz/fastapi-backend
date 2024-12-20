from datetime import datetime

import pytz
from fastapi import HTTPException
from sqlalchemy import BigInteger, Column, DateTime
from starlette import status

from internal.infra.db import Base, get_session
from pkg import format_datetime, get_utc_datetime
from pkg.logger import Logger
from pkg.snow_flake import snowflake_generator


class ModelMixin(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    deleted_at = Column(DateTime, nullable=True, default=None)
    updated_at = Column(DateTime)
    created_at = Column(DateTime)

    async def save(self):
        try:
            async with get_session() as sess:
                sess.add(self)
                await sess.commit()
        except Exception as e:
            Logger.error(f"{self.__class__.__name__} save error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="save error")

    @classmethod
    def create(cls, **kwargs) -> 'ModelMixin':
        cur_datetime = get_utc_datetime()
        instance = cls(id=snowflake_generator.generate_id(), created_at=cur_datetime, updated_at=cur_datetime)
        instance._populate(kwargs)
        return instance

    def update_fields(self, data: dict):
        self._populate(data)

    def compare_diff_fields(self, data: dict) -> dict[str: [str]]:
        diff = {}

        model_columns = self.__mapper__.c.keys()
        for col, value in data.items():
            if col not in model_columns:
                continue

            old_val = getattr(self, col)
            if isinstance(old_val, datetime):
                # 数据库查出来的数据不带时区信息，需要增加时区信息
                old_val = old_val.replace(tzinfo=pytz.UTC)

            if old_val != value:
                diff[col] = [old_val, value]
        return diff

    def _populate(self, data: dict):
        # 使用 __mapper__.c 遍历字段以提高效率
        cols = self.__mapper__.c.keys()
        for col, value in data.items():
            if col in cols:
                setattr(self, col, value)

    def to_dict(self) -> dict:
        d = {}
        for col in self.__mapper__.c.keys():
            val = getattr(self, col)
            if isinstance(val, datetime):
                val = format_datetime(val)
            d[col] = val
        return d

    def mixin_check_required_fields(self, fields: list[str]) -> (str, bool):
        for field in fields:
            val = getattr(self, field)
            if not val:
                return field, False
        return "", True
