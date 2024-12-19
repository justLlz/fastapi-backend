from decimal import Decimal
from typing import Any, Optional, Type, Union

from fastapi import HTTPException

from sqlalchemy import Column, ColumnElement, Select, asc, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from internal.infra.db import get_session
from internal.models.mixin import ModelMixin
from internal.utils.mixin_type import MixinModelType, MixinValType, normalize_column
from pkg import get_utc_datetime, unique_iterable
from pkg.logger import Logger


class Sort:
    ASC: str = "asc"
    DESC: str = "desc"


class BaseBuilder:
    def __init__(self, base_model: Type[ModelMixin]):
        self.model = base_model
        self.stmt: Select = Select()

    def add_conditions(
            self,
            conditions: list[tuple[InstrumentedAttribute | Column, MixinValType]],
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

    def where(self, col: InstrumentedAttribute | Column, value: MixinValType) -> 'BaseBuilder':
        """
        Add a single AND condition to the query.

        :param col: The column for the condition.
        :param value: The value for the condition.
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions([(col, value)], logical_operator="and")

    def where_cond(self, *conditions: tuple[InstrumentedAttribute | Column, MixinValType]) -> "BaseBuilder":
        """
        Add multiple AND conditions to the query.
        :param conditions: A list of tuples where each tuple is (column, value).
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions(list(conditions), logical_operator="and")

    def or_(self, col: InstrumentedAttribute | Column, value: MixinValType) -> 'BaseBuilder':
        """
        Add a single OR condition to the query.
        :param col: The column for the condition.
        :param value: The value for the condition.
        :return: The current instance of BaseBuilder.
        """
        return self.add_conditions([(col, value)], logical_operator="or")

    def or_cond(self, *conditions: tuple[InstrumentedAttribute | Column, MixinValType]) -> 'BaseBuilder':
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
    def __init__(self, model: Type[ModelMixin]):
        super().__init__(model)
        self.stmt: Select = select(self.model).where(model.deleted_at.is_(None))

    def order_by(self, col: Optional[InstrumentedAttribute | Column], sort: str = Sort.DESC) -> 'QueryBuilder':
        col = normalize_column(col)
        self.stmt = self.stmt.order_by(asc(col) if sort == Sort.ASC else desc(col))
        return self

    def paginate(self, page: Optional[int] = None, limit: Optional[int] = None) -> 'QueryBuilder':
        if page and limit:
            self.stmt = self.stmt.offset((page - 1) * limit).limit(limit)
        return self

    async def scalars_all(self, session: Optional[AsyncSession] = None) -> list['MixinModelType']:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().all()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return [i for i in data]

    async def scalar_one_or_none(self, session: Optional[AsyncSession] = None) -> Optional[MixinModelType]:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar_one_or_none()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data

    async def scalars_first(self, session: Optional[AsyncSession] = None) -> Optional[MixinModelType]:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().first()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data

    async def get_or_exec(self, session: Optional[AsyncSession] = None) -> Optional[MixinModelType]:
        data = await self.get_or_none(session)
        if not data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="not found")
        return data

    async def get_or_none(self, session: Optional[AsyncSession] = None) -> Optional[MixinModelType]:
        data = await self.scalar_one_or_none(session)
        return data


class CountBuilder(BaseBuilder):
    def __init__(self, base_model: Type[ModelMixin], col: InstrumentedAttribute | Column = None):
        if col is not None and not isinstance(col, (InstrumentedAttribute, Column)):
            raise ValueError(f"Unsupported type for 'col': {type(col).__name__}. Expected InstrumentedAttribute.")

        super().__init__(base_model)
        col = self.model.id if col is None else col
        self.stmt = select(func.count(col)).where(base_model.deleted_at.is_(None))

    async def count_value(self, session: Optional[AsyncSession] = None) -> int:
        async with get_session(session) as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
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
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    @classmethod
    async def save(cls, ins: ModelMixin, session: Optional[AsyncSession] = None):
        async with get_session(session) as sess:
            try:
                sess.add(ins)
                await sess.commit()
            except Exception as e:
                Logger.error(f"{cls.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
