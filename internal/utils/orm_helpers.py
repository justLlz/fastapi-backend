from typing import Any, Optional, Tuple, Type, Union

from fastapi import HTTPException
from sqlalchemy import (ColumnElement, ColumnExpressionArgument,
                        Delete, Select, Update, asc, desc, func, or_, select, update)
from sqlalchemy.orm import InstrumentedAttribute
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from internal.infra.db import get_session
from internal.models import ModelMixin
from internal.utils.context import get_user_id_context_var
from internal.utils.mixin_type import MixinModelType
from pkg import utc_datetime_with_no_tz
from pkg.logger_helper import logger


class Sort:
    ASC: str = "asc"
    DESC: str = "desc"


class BaseBuilder:
    def __init__(self, base_model: Type[ModelMixin]):
        self._model = base_model
        self._stmt: Select | Delete | Update | None = None

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
        self._stmt = self._stmt.where(or_(*conditions))
        return self

    def distinct(self) -> "BaseBuilder":
        self._stmt = self._stmt.distinct()
        return self

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
        self._stmt = self._stmt.where(*conditions)
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
            column = self._model.get_column_or_none(column_name)
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
            self._stmt = self._stmt.where(*conditions)
        return self


class QueryBuilder(BaseBuilder):
    def __init__(self, model: Type[ModelMixin]):
        super().__init__(model)
        self._stmt: Select = select(self._model).where(model.deleted_at.is_(None))

    @property
    def select_stmt(self) -> Select:
        return self._stmt

    async def scalars_all(self) -> list[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalars().all()
            except Exception as e:
                logger.error(f"{self._model.__name__} scalars_all: {repr(e)}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return [i for i in data]

    async def scalar_one_or_none(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"{self._model.__name__} scalar_one_or_none: {repr(e)}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return data

    async def scalars_first(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalars().first()
            except Exception as e:
                logger.error(f"{self._model.__name__} scalars_first: {repr(e)}")
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
        self._stmt = self._stmt.order_by(asc(col) if sort == Sort.ASC else desc(col))
        return self

    def paginate(self, page: Optional[int] = None, limit: Optional[int] = None) -> "QueryBuilder":
        if page and limit:
            self._stmt = self._stmt.offset((page - 1) * limit).limit(limit)
        return self


class CountBuilder(BaseBuilder):
    def __init__(self, base_model: Type[ModelMixin], column: InstrumentedAttribute = None):
        super().__init__(base_model)
        column = self._model.id if column is None else column
        self._stmt: Select = select(func.count(column)).where(base_model.deleted_at.is_(None))

    @property
    def count_stmt(self) -> Select:
        return self._stmt

    async def count(self) -> int:
        async with get_session() as sess:
            try:
                exec_result = await sess.execute(self._stmt)
                data = exec_result.scalar()
            except Exception as e:
                logger.error(f"{self._model.__name__} count error: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data


class UpdateBuilder(BaseBuilder):
    def __init__(self, base_model: Union[Type[ModelMixin], ModelMixin]):
        super().__init__(base_model if isinstance(base_model, type) else base_model.__class__)
        # 判断 base_model 是否为类，如果是类则创建不带条件的更新语句
        if isinstance(base_model, type):
            self._stmt: Update = update(self._model)
        else:
            # 如果是实例，设置 where 条件以匹配该实例的 id
            self._stmt: Update = update(self._model).where(self._model.id == base_model.id)

        self.update_dict = {}

    def update(self, **kwargs) -> "UpdateBuilder":
        if not kwargs:
            return self

        for column_name, value in kwargs.items():
            column = self._model.get_column_or_none(column_name)
            if column_name is None:
                continue

            self.update_dict[column] = value

        return self

    @property
    def update_stmt(self):
        """生成更新数据库的 SQL 语句（带属性访问器）

        1. 如果没有更新字段，直接返回原语句
        2. 自动处理更新时间字段（线程安全）
        3. 如果涉及软删除字段，同步更新时间
        4. 自动设置更新人字段（如果模型支持）
        """
        # 如果没有需要更新的字段，直接返回原始语句
        if not self.update_dict:
            return self._stmt

        # 获取当前UTC时间（无时区信息，线程安全）
        current_time = utc_datetime_with_no_tz()

        # 获取模型定义的更新时间字段名
        updated_at_column_name = self._model.updated_at_column_name()

        # 特殊处理：如果更新中包含软删除字段（逻辑删除）
        # 则将软删除时间同步到更新时间字段（保持时间一致）
        if deleted_at_column_name := self._model.deleted_at_column_name() in self.update_dict:
            self.update_dict.setdefault(
                updated_at_column_name,
                self.update_dict[deleted_at_column_name]
            )

        # 设置/更新 更新时间字段（如果未设置）
        self.update_dict.setdefault(updated_at_column_name, current_time)

        # 如果模型支持更新人字段，自动设置当前用户ID
        if self._model.has_updater_id_column():
            self.update_dict.setdefault(
                self._model.updater_id_column_name(),
                get_user_id_context_var()  # 从上下文获取当前用户ID
            )

        # 将更新字典应用到SQL语句
        self._stmt = self._stmt.values(**self.update_dict)

        return self._stmt

    async def execute(self):
        if not self.update_dict:
            logger.warning(f"{self._model.__name__} no update data")
            return

        async with get_session() as sess:
            try:
                await sess.execute(self.update_stmt.execution_options(synchronize_session=False))
                await sess.commit()
            except Exception as e:
                logger.error(f"{self._model.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
