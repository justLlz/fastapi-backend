from typing import Any, Optional, Tuple, Type, Union

from fastapi import HTTPException
from sqlalchemy import ColumnElement, ColumnExpressionArgument, Select, asc, desc, func, or_, select, update
from sqlalchemy.orm import InstrumentedAttribute
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from internal.infra.db import get_session
from internal.models import MixinModel
from internal.utils.mixin_type import MixinModelType
from pkg import get_utc_datetime
from pkg.logger_helper import logger


class Sort:
    ASC: str = "asc"
    DESC: str = "desc"


class BaseBuilder:
    def __init__(self, base_model: Type[MixinModel]):
        self.model = base_model
        self.stmt: Select = Select()

    # 单独的操作符方法
    def eq(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """等于条件"""
        return self.where(column == value)

    def ne(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """不等于条件"""
        return self.where(column != value)

    def gt(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """大于条件"""
        return self.where(column > value)

    def lt(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """小于条件"""
        return self.where(column < value)

    def ge(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """大于等于条件"""
        return self.where(column >= value)

    def le(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """小于等于条件"""
        return self.where(column <= value)

    def in_(self, column: InstrumentedAttribute, values: list | tuple) -> "BaseBuilder":
        """包含于列表条件"""
        return self.where(column.in_(values))

    def like(self, column: InstrumentedAttribute, pattern: str) -> "BaseBuilder":
        """模糊匹配条件"""
        return self.where(column.like(f"%{pattern}%"))

    def is_null(self, column: InstrumentedAttribute) -> "BaseBuilder":
        """为空检查条件"""
        return self.where(column.is_(None))

    def between(self, column: InstrumentedAttribute, range_values: Tuple[Any, Any]) -> "BaseBuilder":
        """范围查询条件"""
        return self.where(column.between(range_values[0], range_values[1]))

    def or_(self, *conditions) -> "BaseBuilder":
        """
        添加 OR 条件组合
        示例:
        builder.or_(
            User.name == "Alice",
            User.age > 30
        )
        或:
        conditions = [User.name == "Alice", User.age > 30]
        builder.or_(*conditions)
        """
        if not conditions:
            return self
        self.stmt = self.stmt.where(or_(*conditions))
        return self

    def distinct(self) -> "BaseBuilder":
        self.stmt = self.stmt.distinct()
        return self

    def _get_column(self, column_name: str) -> InstrumentedAttribute:
        column = getattr(self.model, column_name, None)
        if column is None:
            raise HTTPException(
                HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Column {column_name} not found in model {self.model.__name__}",
            )
        return column

    @staticmethod
    def _parse_operator(column: InstrumentedAttribute, operator: str, value: Any) -> ColumnElement:
        """解析操作符并生成条件"""
        if operator == "eq":
            return column == value
        elif operator == "ne":
            return column != value
        elif operator == "gt":
            return column > value
        elif operator == "lt":
            return column < value
        elif operator == "ge":
            return column >= value
        elif operator == "le":
            return column <= value
        elif operator == "in":
            return column.in_(value)
        elif operator == "like":
            return column.like(f"%{value}%")
        elif operator == "is_null":
            return column.is_(None)
        elif operator == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise HTTPException(
                    400,
                    detail="Operator between requires a list/tuple with two values",
                )
            return column.between(value[0], value[1])
        else:
            raise HTTPException(
                400,
                detail=f"Unsupported operator: {operator}",
            )

    def where(self, *conditions: ColumnExpressionArgument[bool]) -> "BaseBuilder":
        """
        example:
        builder = QueryBuilder(MyModel)
        builder.where_v1(MyModel.id == 1, MyModel.name == "Alice")
        stmt = builder.stmt  # SELECT * FROM my_model WHERE id = 1 AND name = "Alice"

        example:
        filters = [MyModel.id == 1, MyModel.name == "Alice"]
        builder.where_v1(*filters)
        """
        self.stmt = self.stmt.where(*conditions)
        return self

    def where_by(self, **kwargs) -> "BaseBuilder":
        """
        支持 kwargs 的 key 与数据库字段名一致，value 是操作符字典
        示例:
        where(age={"gt": 30}, status={"in": [1, 2]})
        查询 age > 30, age < 40, deleted_at=null
        where(age={"gt": 30, "lt": 40}， deleted_at={"is_null": True})
        """
        conditions = []
        for column_name, value in kwargs.items():
            # 获取 SQLAlchemy 列对象
            column = self._get_column(column_name)
            # 如果值是字典（支持多个操作符）
            if isinstance(value, dict):
                for operator, val in value.items():
                    condition = self._parse_operator(column, operator, val)
                    conditions.append(condition)
            # 默认等值查询（例如 age=30）
            else:
                conditions.append(column == value)

        # 将所有条件用 AND 连接
        if conditions:
            self.stmt = self.stmt.where(*conditions)
        return self


class QueryBuilder(BaseBuilder):
    def __init__(self, model: Type[MixinModel]):
        super().__init__(model)
        self.stmt: Select = select(self.model).where(model.deleted_at.is_(None))

    async def scalars_all(self) -> list[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().all()
            except Exception as e:
                logger.error(f"{self.model.__name__} scalars_all: {repr(e)}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return [i for i in data]

    async def scalar_one_or_none(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"{self.model.__name__} scalar_one_or_none: {repr(e)}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return data

    async def scalars_first(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalars().first()
            except Exception as e:
                logger.error(f"{self.model.__name__} scalars_first: {repr(e)}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return data

    async def get_or_exec(self) -> Optional[MixinModelType]:
        data = await self.get_or_none()
        if not data:
            raise HTTPException(status_code=404, detail="not found")
        return data

    async def get_or_none(self) -> Optional[MixinModelType]:
        data = await self.scalar_one_or_none()
        return data

    def order_by(self, col: InstrumentedAttribute, sort: str = Sort.DESC) -> "QueryBuilder":
        self.stmt = self.stmt.order_by(asc(col) if sort == Sort.ASC else desc(col))
        return self

    def paginate(self, page: Optional[int] = None, limit: Optional[int] = None) -> "QueryBuilder":
        if page and limit:
            self.stmt = self.stmt.offset((page - 1) * limit).limit(limit)
        return self


class CountBuilder(BaseBuilder):
    def __init__(self, base_model: Type[MixinModel], col: InstrumentedAttribute = None):
        super().__init__(base_model)
        col = self.model.id if col is None else col
        self.stmt = select(func.count(col)).where(base_model.deleted_at.is_(None))

    async def count(self) -> int:
        async with get_session() as sess:
            try:
                result = await sess.execute(self.stmt)
                data = result.scalar()
            except Exception as e:
                logger.error(f"{self.model.__name__}: {repr(e)}")
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

    def update(self, **kwargs) -> "UpdateBuilder":
        if not kwargs:
            return self

        model_columns = self.model.__mapper__.c.keys()
        for col, value in kwargs.items():
            if col in model_columns:
                self.update_dict[col] = value

        return self

    def update_by(self, kwargs: dict):
        return self.update(**kwargs)

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
                logger.error(f"{self.model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
