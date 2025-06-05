"""该目录主要用于数据库模型"""
from typing import Any

from fastapi import HTTPException
from sqlalchemy import BigInteger, Column, DateTime
from sqlalchemy.orm import InstrumentedAttribute
from starlette import status

from internal.infra.db import Base, get_session
from internal.utils.context import get_user_id_context_var
from pkg import get_utc_without_tzinfo
from pkg.logger_helper import logger
from pkg.snowflake_helper import generate_snowflake_id


class ModelMixin(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=False), nullable=False)
    updated_at = Column(DateTime(timezone=False), nullable=True, default=None, server_default=None)
    deleted_at = Column(DateTime(timezone=False), nullable=True, default=None, server_default=None)

    @classmethod
    async def add_all(cls, items: list[dict]):
        if not items:
            return

        ins_list = [cls.create(**item) for item in items]
        try:
            async with get_session() as sess:
                async with sess.begin():
                    sess.add_all(ins_list)
        except Exception as e:
            logger.error(f"{cls.__name__} add_all error: {e}")
            raise e

    async def save(self):
        try:
            async with get_session() as sess:
                sess.add(self)
                await sess.commit()
        except Exception as e:
            logger.error(f"{self.__class__.__name__} save error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def update(self, **kwargs):
        for column_name, value in kwargs.items():
            if not self.has_column(column_name):
                continue
            setattr(self, column_name, value)

        if hasattr(self, self.updated_at_column_name()):
            cur_datetime = get_utc_without_tzinfo()
            setattr(self, self.updated_at_column_name(), cur_datetime)

        if self.has_updater_id_column():
            user_id = get_user_id_context_var()
            setattr(self, self.updater_id_column_name(), user_id)

        try:
            async with get_session() as sess:
                sess.add(self)
                await sess.commit()
        except Exception as e:
            logger.error(f"{self.__class__.__name__} update error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @classmethod
    def create(cls, **kwargs) -> "ModelMixin":
        cur_datetime = get_utc_without_tzinfo()
        instance = cls(created_at=cur_datetime, updated_at=cur_datetime)

        if "id" not in kwargs:
            instance.id = generate_snowflake_id()
        if instance.has_creator_column():
            user_id = get_user_id_context_var()
            setattr(instance, instance.creator_id_column_name(), user_id)
        if instance.has_updater_id_column():
            setattr(instance, instance.updater_id_column_name(), None)
        if instance.has_updated_at_column():
            instance._set_col_maybe_none(instance.updated_at_column_name(), cur_datetime)

        instance.populate(**kwargs)
        return instance

    def populate(self, **kwargs):
        for column_name, value in kwargs.items():
            if not self.has_column(column_name):
                # logger.warning(f"Column '{column_name}' does not exist in model '{self.__class__.__name__}'")
                continue
            setattr(self, column_name, value)

    def to_dict(self) -> dict:
        d = {}
        for column_name in self.get_column_names():
            val = getattr(self, column_name)
            d[column_name] = val
        return d

    def clone(self) -> "ModelMixin":
        excluded_columns = ["updater_id", "creator_id", "updated_at", "deleted_at", "id"]
        data = {k: v for k, v in self.to_dict().items() if k not in excluded_columns}
        return self.create(**data)

    def mixin_check_required_fields(self, fields: list[str]) -> (str, bool):
        for field in fields:
            val = getattr(self, field)
            if not val:
                return field, False
        return "", True

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
    def has_updated_at_column(cls):
        return cls.has_column(cls.updated_at_column_name())

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

    @staticmethod
    def is_utc_column(column_name: str):
        if column_name in ["created_at", "updated_at", "deleted_at"]:
            return True
        else:
            return False

    def _set_col_maybe_none(self, column_name: str, default_value: Any):
        column: InstrumentedAttribute = self.get_column_or_none(column_name)
        if column:
            if column.default is None or column.server_default is None:
                setattr(self, column_name, None)
            else:
                setattr(self, column_name, default_value)
