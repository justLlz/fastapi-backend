"""该目录主要用于数据库模型"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import BigInteger, Column, DateTime
from sqlalchemy.orm import InstrumentedAttribute
from starlette import status

from internal.infra.db import Base, get_session
from internal.utils.context import get_user_id_context_var
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

        if cls.has_creator_column():
            instance.creator_id = get_user_id_context_var()

        instance._populate(**kwargs)
        return instance

    def _populate(self, **kwargs):
        for column_name, value in kwargs.items():
            if not self.has_column(column_name):
                continue
            setattr(self, column_name, value)

    def to_dict(self) -> dict:
        result = {}
        for column_name in self.get_column_names():
            val = getattr(self, column_name)

            if isinstance(val, datetime):
                val = datetime_to_string(val)

            result[column_name] = val
        return result

    @staticmethod
    def updater_id_column_name() -> str:
        return "updater_id"

    @staticmethod
    def creator_id_column_name() -> str:
        return "creator_id"

    @staticmethod
    def updated_at_column_name() -> str:
        return "updated_at"

    @staticmethod
    def deleted_at_column_name() -> str:
        return "deleted_at"

    @classmethod
    def has_deleted_at_column(cls) -> bool:
        """判断是否有删除时间字段"""
        return cls.has_column(cls.deleted_at_column_name())

    @classmethod
    def has_creator_column(cls) -> bool:
        """判断是否有创建人字段"""
        return cls.has_column(cls.creator_id_column_name())

    @classmethod
    def has_updater_id_column(cls) -> bool:
        """判断是否有更新人字段"""
        return cls.has_column(cls.updater_id_column_name())

    @classmethod
    def has_column(cls, column_name: str) -> bool:
        """判断是否为真实数据库字段"""
        return column_name in cls.__table__.columns

    @classmethod
    def get_column_names(cls) -> list[str]:
        return list(cls.__table__.columns.keys())

    @classmethod
    def get_column_or_none(cls, column_name: str) -> InstrumentedAttribute | None:
        if column_name not in cls.__table__.columns:
            logger.warning(f"{column_name} is not a real table column of {cls.__name__}")
            return None
        return getattr(cls, column_name)

    @classmethod
    def get_column_or_raise(cls, column_name: str) -> InstrumentedAttribute:
        if column_name not in cls.__table__.columns:
            raise HTTPException(
                400,
                detail=f"{column_name} is not a real table column of {cls.__name__}",
            )
        return getattr(cls, column_name)
