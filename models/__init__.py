from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Type, TypeVar, Union

import pytz
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import (BigInteger, Column, ColumnElement, DateTime, Select, Update, asc, desc, func,
                        or_, select, update)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from utils import get_utc_datetime, unique_iterable
from utils.db_helper import Base, get_session
from utils.snow_flake import snowflake_generator

TModelMixin = TypeVar("TModelMixin", bound="ModelMixin")  # 定义一个泛型变量 T，继承自 ModelMixin

ValType = Union[list, set, tuple, frozenset, str, int, float, bool, Decimal, None]


class Sort:
    ASC: str = "asc"
    DESC: str = "desc"


class ModelMixin(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    deleted_at = Column(DateTime, nullable=True, default=None)
    updated_at = Column(DateTime)
    created_at = Column(DateTime)

    @classmethod
    def _base_filters(cls) -> list:
        """Reusable query filters."""
        return [cls.deleted_at.is_(None)]

    @classmethod
    def base_query_stmt(cls) -> Select[Any]:
        return select(cls).where(*cls._base_filters())

    @classmethod
    def base_count_stmt(cls, column: Column | InstrumentedAttribute) -> Select[Any]:
        return select(func.count(column)).where(*cls._base_filters())

    def base_update_stmt(self, data: Union[dict, BaseModel] = None) -> Update:
        """生成 update 语句"""
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)
        # 过滤出仅包含值发生变化的字段
        fields_to_update = {
            k: v for k, v in data.items()
            if k in self.__mapper__.c.keys() and getattr(self, k) != v
        }

        stmt = update(self.__class__).where(self.__class__.id == self.id)
        stmt = stmt.values(fields_to_update) if fields_to_update else stmt
        return stmt

    async def save(self, session: Optional[AsyncSession] = None):
        try:
            async with get_session(session) as sess:
                sess.add(self)
                await sess.commit()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f'{self.__class__.__name__} save error: {e}')

    async def update(self, data: Union[dict, BaseModel], session: Optional[AsyncSession] = None):
        stmt = self.base_update_stmt(data)
        try:
            async with get_session(session) as sess:
                await sess.execute(stmt.execution_options(synchronize_session=False))
                await sess.commit()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f'{self.__class__.__name__} update error: {e}')

    async def logical_delete(self, session: Optional[AsyncSession] = None):
        cur_datetime = get_utc_datetime()
        await self.update({'deleted_at': cur_datetime}, session)

    @classmethod
    def create(cls, data: Union[dict, BaseModel]) -> 'ModelMixin':
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)

        cur_datetime = get_utc_datetime()
        instance = cls(id=snowflake_generator.generate_id(), created_at=cur_datetime, updated_at=cur_datetime)
        instance._populate(data)
        return instance

    def update_fields(self, data: Union[dict, BaseModel]):
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)
        self._populate(data)

    def compare_fields(self, data: Union[dict, BaseModel]) -> dict[str: [str]]:
        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True)

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
            d[col] = getattr(self, col)
        return d

    def remote_to_dict(self):
        d = {}
        for col in self.__mapper__.c.keys():
            # 检查是否为 datetime 类型
            if isinstance(attr := getattr(self, col), datetime):
                # 如果时间没有时区信息，假设为东八区时间
                if attr.tzinfo is None:
                    attr = pytz.timezone('Asia/Shanghai').localize(attr)

                # 转换为 UTC 时间并移除时区信息
                d[col] = attr.astimezone(pytz.utc).replace(tzinfo=None)
            else:
                d[col] = attr
        return d

    @classmethod
    def where_case(cls, col: InstrumentedAttribute | Column, value: ValType) -> list:
        col = normalize_column(col)
        where_cases = [col == value]
        return where_cases


class BaseBuilder:
    def __init__(self, base_model: Type[ModelMixin]):
        self.model = base_model
        self.stmt: Select[Any] = select(self.model)

    def add_conditions(
            self,
            conditions: list[tuple[InstrumentedAttribute | Column, ValType]],
            logical_operator: str = "and"
    ) -> 'BaseBuilder':
        """
        Add conditions (AND/OR) to the query.

        :param conditions: A list of tuples where each tuple is (column, value).
        :param logical_operator: "and" for AND conditions, "or" for OR conditions.
        :return: The current instance of BaseBuilder.
        """
        parsed_conditions: list[ColumnElement[bool]] = []

        for cond in conditions:
            col, value = cond
            col = normalize_column(col)
            match value:
                case list() | set() | tuple() | frozenset():
                    value = unique_iterable(value)
                    parsed_conditions.append(col.in_(value))
                case str() | int() | float() | bool() | Decimal():
                    parsed_conditions.append(col == value)
                case None:
                    parsed_conditions.append(col.is_(None))
                case _:
                    raise ValueError(
                        f"Unsupported type for 'value': {type(value).__name__}. "
                        f"Expected list, set, tuple, str, int, float, bool, Decimal, or None."
                    )

        if parsed_conditions:
            if logical_operator == "or":
                self.stmt = self.stmt.where(or_(*parsed_conditions))
            elif logical_operator == "and":
                for condition in parsed_conditions:
                    self.stmt = self.stmt.where(condition)
            else:
                raise ValueError(f"Unsupported logical operator: {logical_operator}")

        return self

    def where(self, col: InstrumentedAttribute | Column, value: ValType) -> 'BaseBuilder':
        """
        Add a single AND condition to the query.

        :param col: The column for the condition.
        :param value: The value for the condition.
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions([(col, value)], logical_operator="and")

    def where_cond(self, *conditions: tuple[InstrumentedAttribute | Column, ValType]) -> 'BaseBuilder':
        """
        Add multiple AND conditions to the query.
        :param conditions: A list of tuples where each tuple is (column, value).
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions(list(conditions), logical_operator="and")

    def or_(self, col: InstrumentedAttribute | Column, value: ValType) -> 'BaseBuilder':
        """
        Add a single OR condition to the query.
        :param col: The column for the condition.
        :param value: The value for the condition.
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions([(col, value)], logical_operator="or")

    def or_cond(self, *conditions: tuple[InstrumentedAttribute | Column, ValType]) -> 'BaseBuilder':
        """
        Add multiple OR conditions to the query.

        :param conditions: A list of tuples where each tuple is (column, value).
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions(list(conditions), logical_operator="or")

    def not_deleted(self) -> 'BaseBuilder':
        self.add_conditions([(self.model.deleted_at, None)])
        return self


class QueryBuilder(BaseBuilder):
    def __init__(self, base_model: Type[ModelMixin]):
        super().__init__(base_model)
        self.stmt = self.model.base_query_stmt()

    def order_by(self, col: Optional[InstrumentedAttribute | Column], sort: str = Sort.DESC) -> 'QueryBuilder':
        col = normalize_column(col)
        self.stmt = self.stmt.order_by(asc(col) if sort == Sort.ASC else desc(col))
        return self

    def paginate(self, page: Optional[int] = None, limit: Optional[int] = None) -> 'QueryBuilder':
        if page and limit:
            self.stmt = self.stmt.offset((page - 1) * limit).limit(limit)
        return self

    async def scalars_all(self, session: Optional[AsyncSession] = None) -> list[TModelMixin]:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().all()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.model.__name__} get_multiple error: {e}')
        return [i for i in data]

    async def scalar_one_or_none(self, session: Optional[AsyncSession] = None) -> TModelMixin | None:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar_one_or_none()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.model.__name__} get error: {e}')
        return data

    async def scalars_first(self, session: Optional[AsyncSession] = None) -> TModelMixin | None:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().first()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.model.__name__} get error: {e}')
        return data

    async def get_or_exec(self, session: Optional[AsyncSession] = None) -> Optional[TModelMixin]:
        data = await self.get_or_none(session)
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f'{self.model.__name__} not found')
        return data

    async def get_or_none(self, session: Optional[AsyncSession] = None) -> TModelMixin | None:
        data = await self.scalar_one_or_none(session)
        return data


class CountBuilder(BaseBuilder):
    def __init__(self, base_model: Type[ModelMixin], col: InstrumentedAttribute | Column = None):
        if col is not None and not isinstance(col, (InstrumentedAttribute, Column)):
            raise ValueError(f"Unsupported type for 'col': {type(col).__name__}. Expected InstrumentedAttribute.")

        super().__init__(base_model)
        col = self.model.id if col is None else col
        self.stmt = self.model.base_count_stmt(col)

    async def count_value(self, session: Optional[AsyncSession] = None) -> int:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.model.__name__} count error: {e}')
        return data


class UpdateBuilder(BaseBuilder):
    def __init__(self, base_model: Union[Type[ModelMixin], ModelMixin]):
        super().__init__(base_model if isinstance(base_model, type) else base_model.__class__)
        # 判断 base_model 是否为类，如果是类则创建不带条件的更新语句
        if isinstance(base_model, type):
            self.stmt = update(self.model)
        else:
            # 如果是实例，设置 where 条件以匹配该实例的 id
            self.stmt = update(self.model).where(self.model.id == base_model.id)

        self.stmt = self.stmt.values(**{"updated_at": get_utc_datetime()})

    def values(self, **kwargs) -> 'UpdateBuilder':
        if not kwargs:
            return self

        update_dict: dict[str, Any] = {}
        model_columns = self.model.__mapper__.c.keys()
        for col, value in kwargs.items():
            if col in model_columns:
                update_dict[col] = value

        if update_dict:
            self.stmt = self.stmt.values(**update_dict)

        return self

    async def execute(self, session: Optional[AsyncSession] = None):
        self.stmt = self.stmt.values(updated_at=get_utc_datetime())
        async with get_session(session) as sess:
            try:
                await sess.execute(self.stmt.execution_options(synchronize_session=False))
                await sess.commit()
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail=f'{self.model.__name__} update error: {e}')


def normalize_column(col: InstrumentedAttribute | Column) -> ColumnElement:
    if isinstance(col, InstrumentedAttribute):
        return col.__clause_element__()
    elif isinstance(col, Column):
        return col
    else:
        raise ValueError(
            f"Unsupported type for 'col': {type(col).__name__}. "
            f"Expected InstrumentedAttribute or Column."
        )
