import traceback
from typing import Any, Optional, Tuple, Type, Union

from fastapi import HTTPException
from sqlalchemy import (ColumnElement, ColumnExpressionArgument,
                        Delete, Select, Update, asc, delete, desc, func, or_, select, update)
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
    """SQL查询构建器基类，提供模型类和方法的基本结构"""

    __slots__ = ('_model_cls', '_stmt')  # 优化内存使用

    def __init__(self, *, model_cls: Type[MixinModelType]) -> None:
        """
        初始化查询构建器

        Args:
            model_cls: 要操作的模型类，必须是 ModelMixin 的子类

        Raises:
            TypeError: 如果 model_cls 不是有效的模型类
        """
        if not isinstance(model_cls, type) or not issubclass(model_cls, ModelMixin):
            raise HTTPException(500,
                                f"model_cls must be a subclass of ModelMixin, and actually gets: {type(model_cls)}")

        self._model_cls: Type[MixinModelType] = model_cls
        self._stmt: Union[Select, Delete, Update, None] = None

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
                raise HTTPException(400, "Operator between requires a list/tuple with two values",
                                    )
            return column.between(value[0], value[1])
        else:
            raise HTTPException(400, f"Unsupported operator: {operator}")

    def _apply_soft_delete(self) -> None:
        """安全地添加软删除过滤条件"""
        deleted_column = self._model_cls.get_column_or_none(self._model_cls.deleted_at_column_name())
        self._stmt = self._stmt.where(deleted_column.is_(None))

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
            if not isinstance(column_name, str):
                logger.warning(f"invalid column name: {column_name}, must be str")
                continue
            # 获取 SQLAlchemy 列对象
            column = self._model_cls.get_column_or_none(column_name)
            if column is None:
                continue

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
    def __init__(
            self,
            model_cls: Type[ModelMixin],
            *,
            include_deleted: bool = False,
            initial_where: Optional[ColumnElement] = None
    ):
        """
        查询构建器基础类

        Args:
            model_cls: 要查询的模型类
            include_deleted: 是否包含已软删除的记录 (默认False)
            initial_where: 初始WHERE条件 (可选)

        Raises:
            ValueError: 如果模型类无效
        """
        super().__init__(model_cls=model_cls)

        # 基础查询语句
        self._stmt: Select = select(self._model_cls)

        # 默认过滤已删除记录
        if not include_deleted and self._model_cls.has_deleted_at_column:
            self._apply_soft_delete()

        # 添加初始WHERE条件
        if initial_where is not None:
            self._stmt = self._stmt.where(initial_where)

    @property
    def select_stmt(self) -> Select:
        return self._stmt

    async def scalars_all(self) -> list[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalars().all()
            except Exception as e:
                logger.error(f"{self._model_cls.__name__} scalars_all error: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return [i for i in data]

    async def scalar_one_or_none(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"{self._model_cls.__name__} scalar_one_or_none error: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        return data

    async def scalars_first(self) -> Optional[MixinModelType]:
        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalars().first()
            except Exception as e:
                logger.error(f"{self._model_cls.__name__} scalars_first: {repr(e)}")
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
    def __init__(
            self,
            model_cls: Type[ModelMixin],
            count_column: Optional[InstrumentedAttribute] = None,
            *,
            include_deleted: bool = False
    ):
        """
        计数查询构建器

        参数:
            model_cls: 要计数的模型类
            count_column: 要计数的列（默认为主键ID）
            include_deleted: 是否包含已软删除的记录（默认False）
        """
        super().__init__(model_cls=model_cls)

        # 设置计数列（默认为主键）
        self._count_column = count_column if count_column is not None else self._model_cls.id

        # 构建基础查询
        self._stmt: Select = select(func.count(self._count_column))

        # 默认过滤已删除记录
        if not include_deleted and self._model_cls.has_deleted_at_column():
            self._apply_soft_delete()

    @property
    def count_stmt(self) -> Select:
        return self._stmt

    async def count(self) -> int:
        async with get_session() as sess:
            try:
                exec_result = await sess.execute(self._stmt)
                data = exec_result.scalar()
            except Exception as e:
                logger.error(f"{self._model_cls.__name__} count error: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
        return data


class UpdateBuilder(BaseBuilder):
    def __init__(
            self,
            *,
            model_cls: Optional[Type[ModelMixin]] = None,
            model_instance: Optional[ModelMixin] = None
    ):
        """
        更新构建器初始化

        参数:
            model_cls: 要更新的模型类（用于批量更新）
            model_instance: 要更新的模型实例（用于单条记录更新）

        注意:
            - 必须且只能提供 model_cls 或 model_instance 中的一个
            - 如果提供 model_instance，会自动添加 WHERE id=instance.id 条件
        """
        # 参数校验
        if (model_cls is None) == (model_instance is None):
            raise HTTPException(500, "must and can only provide one of model_cls or model_instance")

        model_cls = model_cls if model_cls is not None else model_instance.__class__
        # 调用父类初始化
        super().__init__(model_cls=model_cls)

        # 初始化更新语句
        self._stmt: Update = update(self._model_cls)
        self._update_dict = {}

        # 如果是实例更新，添加ID条件
        if model_instance is not None:
            model_id_column: InstrumentedAttribute = self._model_cls.get_column_or_none("id")
            self._stmt = self._stmt.where(model_id_column == model_instance.id)

    def update(self, **kwargs) -> "UpdateBuilder":
        if not kwargs:
            return self

        for column_name, value in kwargs.items():
            if not self._model_cls.has_column(column_name):
                continue

            self._update_dict[column_name] = value

        return self

    def soft_delete(self) -> "UpdateBuilder":
        """软删除更新"""
        if not self._model_cls.has_deleted_at_column():
            return self
        self._update_dict[self._model_cls.deleted_at_column_name()] = utc_datetime_with_no_tz()
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
        if not self._update_dict:
            return self._stmt

        # 获取当前UTC时间（无时区信息，线程安全）
        current_time = utc_datetime_with_no_tz()

        # 获取模型定义的更新时间字段名
        updated_at_column_name = self._model_cls.updated_at_column_name()

        # 特殊处理：如果更新中包含软删除字段（逻辑删除）
        # 则将软删除时间同步到更新时间字段（保持时间一致）
        if (deleted_at_column_name := self._model_cls.deleted_at_column_name()) in self._update_dict:
            self._update_dict.setdefault(
                updated_at_column_name,
                self._update_dict[deleted_at_column_name]
            )

        # 设置/更新 更新时间字段（如果未设置）
        self._update_dict.setdefault(updated_at_column_name, current_time)

        # 如果模型支持更新人字段，自动设置当前用户ID
        if self._model_cls.has_updater_id_column():
            self._update_dict.setdefault(
                self._model_cls.updater_id_column_name(),
                get_user_id_context_var()  # 从上下文获取当前用户ID
            )

        # 将更新字典应用到SQL语句
        self._stmt = self._stmt.values(**self._update_dict)

        return self._stmt

    async def execute(self):
        if not self._update_dict:
            logger.warning(f"{self._model_cls.__name__} no update data")
            return

        async with get_session() as sess:
            try:
                await sess.execute(self.update_stmt.execution_options(synchronize_session=False))
                await sess.commit()
            except Exception as e:
                logger.error(f"{self._model_cls.__name__}: {repr(e)}")
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e


class DeleteBuilder(BaseBuilder):
    """删除构建器，支持物理删除操作

    特性:
        - 支持通过模型类或模型实例初始化
        - 支持批量删除条件构建
        - 自动化的错误处理和日志记录
        - 一致的 API 设计风格
    """

    def __init__(
            self,
            *,
            model_cls: Optional[Type[ModelMixin]] = None,
            model_instance: Optional[ModelMixin] = None
    ):
        """
        删除构建器初始化

        参数:
            model_cls: 要删除的模型类（用于批量删除）
            model_instance: 要删除的模型实例（用于单条记录删除）

        注意:
            - 必须且只能提供 model_cls 或 model_instance 中的一个
            - 如果提供 model_instance，会自动添加 WHERE id=instance.id 条件
        """
        # 参数校验
        if (model_cls is None) == (model_instance is None):
            raise HTTPException(500, "must and can only provide one of model_cls or model_instance")

        model_cls: Optional[Type[ModelMixin]] = model_cls if model_cls is not None else model_instance.__class__
        # 调用父类初始化
        super().__init__(model_cls=model_cls)

        # 初始化删除语句
        self._stmt: Delete = delete(self._model_cls)

        # 如果是实例删除，添加ID条件
        if model_instance is not None:
            model_id_column: InstrumentedAttribute = self._model_cls.get_column_or_none("id")
            self._stmt = self._stmt.where(model_id_column == model_instance.id)

    @property
    def delete_stmt(self) -> Delete:
        """获取最终的删除语句（带属性访问器）"""
        return self._stmt

    async def execute(self) -> int:
        """执行删除操作

        返回:
            删除的记录数

        异常:
            HTTPException: 当删除操作失败时抛出
        """
        async with get_session() as sess:
            try:
                result = await sess.execute(self.delete_stmt.execution_options(synchronize_session=False))
                await sess.commit()

                deleted_count = result.rowcount
                if deleted_count == 0:
                    logger.warning(f"No records deleted from {self._model_cls.__name__}")
                else:
                    logger.info(f"Successfully deleted {deleted_count} records from {self._model_cls.__name__}")

                return deleted_count

            except Exception as e:
                logger.error(f"{self._model_cls.__name__} delete error: {traceback.format_exc()}")
                raise HTTPException(500, f"Failed to delete records: {str(e)}") from e
