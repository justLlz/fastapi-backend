"""
该目录主要用于数据库操作
"""
from decimal import Decimal
from typing import Optional, Type, Union

from fastapi import HTTPException
from sqlalchemy import Column, ColumnElement, Select, asc, desc, func, or_, select, update
from sqlalchemy.orm import InstrumentedAttribute
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from internal.infra.db import get_session
from internal.models import MixinModel
from internal.utils.mixin_type import MixinModelType, MixinValType, normalize_column
from pkg import get_utc_datetime, unique_iterable
from pkg.logger import Logger


class Sort:
    ASC: str = "asc"
    DESC: str = "desc"


class BaseBuilder:
    def __init__(self, base_model: Type[MixinModel]):
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

    def where_v1(self, *conditions) -> "BaseBuilder":
        """
        example:
        builder = QueryBuilder(MyModel)
        builder.where_v1(MyModel.id == 1, MyModel.name == "Alice")
        stmt = builder.stmt  # SELECT * FROM my_model WHERE id = 1 AND name = 'Alice'

        example:
        filters = [MyModel.id == 1, MyModel.name == "Alice"]
        builder.where_v1(*filters)
        """
        self.stmt = self.stmt.where(*conditions)
        return self

    def where_v2(self, col: InstrumentedAttribute | Column, value: MixinValType) -> 'BaseBuilder':
        """
        Add a single AND condition to the query.

        :param col: The column for the condition.
        :param value: The value for the condition.
        :return: The current instance of BaseBuilder.

        example:
        builder = QueryBuilder(MyModel)
        builder.where_v2(MyModel.id, 1)
        stmt = builder.stmt  # SELECT * FROM my_model WHERE id = 1
        """
        return self.add_conditions([(col, value)], logical_operator="and")

    def where_v3(self, *conditions: tuple[InstrumentedAttribute | Column, MixinValType]) -> "BaseBuilder":
        """
        Add multiple AND conditions to the query.
        :param conditions: A list of tuples where each tuple is (column, value).
        :return: The current instance of BaseBuilder.
        example:
        # 查询 id 为 1 且 name 为 "Alice" 的记录
        builder = QueryBuilder(MyModel)
        builder.where_v3((MyModel.id, 1), (MyModel.name, "Alice"))
        stmt = builder.stmt  # SELECT * FROM my_model WHERE id = 1 AND name = 'Alice'
        """
        return self.add_conditions(list(conditions), logical_operator="and")

    def or_cond(self, *conditions) -> 'BaseBuilder':
        self.stmt = self.stmt.where(or_(*conditions))
        return self


class QueryBuilder(BaseBuilder):
    def __init__(self, model: Type[MixinModel]):
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

    async def scalars_all(self) -> list['MixinModelType']:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().all()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return [i for i in data]

    async def scalar_one_or_none(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar_one_or_none()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data

    async def scalars_first(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().first()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data

    async def get_or_exec(self) -> Optional[MixinModelType]:
        data = await self.get_or_none()
        if not data:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="not found")
        return data

    async def get_or_none(self) -> Optional[MixinModelType]:
        data = await self.scalar_one_or_none()
        return data


class CountBuilder(BaseBuilder):
    def __init__(self, base_model: Type[MixinModel], col: InstrumentedAttribute | Column = None):
        if col is not None and not isinstance(col, (InstrumentedAttribute, Column)):
            raise ValueError(f"Unsupported type for 'col': {type(col).__name__}. Expected InstrumentedAttribute.")

        super().__init__(base_model)
        col = self.model.id if col is None else col
        self.stmt = select(func.count(col)).where(base_model.deleted_at.is_(None))

    async def count(self) -> int:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data


class UpdateBuilder(BaseBuilder):
    def __init__(self, base_model: Union[Type[MixinModel], MixinModel]):
        super().__init__(base_model if isinstance(base_model, type) else base_model.__class__)
        # 判断 base_model 是否为类，如果是类则创建不带条件的更新语句
        if isinstance(base_model, type):
            self.stmt = update(self.model)
        else:
            # 如果是实例，设置 where 条件以匹配该实例的 id
            self.stmt = update(self.model).where(self.model.id == base_model.id)

        self.update_dict = {}

    def update(self, kwargs: dict) -> 'UpdateBuilder':
        if not kwargs:
            return self

        model_columns = self.model.__mapper__.c.keys()
        for col, value in kwargs.items():
            if col in model_columns:
                self.update_dict[col] = value

        return self

    async def execute(self):
        if not self.update_dict:
            return

        # 时间字段处理（线程安全版）
        current_time = get_utc_datetime()
        if "deleted_at" in self.update_dict:
            self.update_dict.setdefault("updated_at", self.update_dict["deleted_at"])
        self.update_dict.setdefault("updated_at", current_time)

        self.stmt = self.stmt.values(**self.update_dict)

        async with get_session() as sess:
            try:
                await sess.execute(self.stmt.execution_options(synchronize_session=False))
                await sess.commit()
            except Exception as e:
                Logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

    @classmethod
    async def save(cls, ins: MixinModel):
        async with get_session() as sess:
            try:
                sess.add(ins)
                await sess.commit()
            except Exception as e:
                Logger.error(f"{cls.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
