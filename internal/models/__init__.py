"""该目录主要用于数据库模型"""
from datetime import datetime

import pytz
from fastapi import HTTPException
from sqlalchemy import BigInteger, Column, DateTime
from starlette import status

from internal.infra.db import Base, get_session
from pkg import datetime_to_string, utc_datetime
from pkg.logger_helper import logger
from pkg.snow_flake import generate_snowflake_id


class ModelMixin(Base):
    """统一存UTC时间不带时区信息"""
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(False))
    updated_at = Column(DateTime(False))
    deleted_at = Column(DateTime(False), nullable=True, default=None)

    async def save(self):
        try:
            async with get_session() as sess:
                sess.add(self)
                await sess.commit()
        except Exception as e:
            logger.error(f"{self.__class__.__name__} save error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="db save error")

    @classmethod
    def create(cls, **kwargs) -> "ModelMixin":
        cur_datetime = utc_datetime()
        instance = cls(id=generate_snowflake_id(), created_at=cur_datetime, updated_at=cur_datetime)
        instance._populate(kwargs)
        return instance

    def compare_diff_fields(self, data: dict) -> dict[str: [str]]:
        diff = {}

        model_columns = self.__mapper__.c.keys()
        for col, value in data.items():
            if col not in model_columns:
                continue

            old_val = getattr(self, col)
            if isinstance(old_val, datetime):
                old_val = old_val.replace(tzinfo=pytz.UTC)

            if old_val != value:
                diff[col] = [old_val, value]
        return diff

    def _populate(self, data: dict):
        cols = self.__mapper__.c.keys()
        for col, value in data.items():
            if col in cols:
                setattr(self, col, value)

    def to_dict(self) -> dict:
        d = {}
        for col in self.__mapper__.c.keys():
            val = getattr(self, col)
            if isinstance(val, datetime):
                val = datetime_to_string(val)
            d[col] = val
        return d

    def mixin_check_required_fields(self, fields: list[str]) -> (str, bool):
        for field in fields:
            val = getattr(self, field)
            if not val:
                return field, False
        return "", True
