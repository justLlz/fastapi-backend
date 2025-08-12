import traceback
from datetime import datetime
from typing import Any

from sqlalchemy import (Column, ColumnExpressionArgument, Delete, Function, Select, Subquery, Update,
                        delete, distinct, func, or_, select, update)
from sqlalchemy.orm import InstrumentedAttribute, aliased
from sqlalchemy.sql.elements import BinaryExpression, ClauseElement

from internal.infra.db import get_session
from internal.models import ModelMixin
from internal.utils.context import get_user_id_context_var
from internal.utils.mixin_type import MixinModelType
from pkg import get_utc_without_tzinfo
from pkg.exception import AppException

from pkg.logger_helper import logger


class BaseBuilder:
    """SQL查询构建器基类，提供模型类和方法的基本结构"""

    __slots__ = ('_model_cls', '_stmt')  # 优化内存使用

    def __init__(self, model_cls: type[MixinModelType]) -> None:
        """
        初始化查询构建器

        Args:
            model_cls: 要操作的模型类，必须是 ModelMixin 的子类

        Raises:
            TypeError: 如果 model_class 不是有效的模型类
        """
        if not isinstance(model_cls, type) or not issubclass(model_cls, ModelMixin):
            raise AppException(
                500, f"model_class must be a subclass of ModelMixin, and actually gets: {type(model_cls)}",
            )

        self._model_cls: type[MixinModelType] = model_cls
        self._stmt: Select | Delete | Update | None = None

    # 单独的操作符方法
    def eq_(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """等于条件"""
        return self.where(column == value)

    def ne_(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """不等于条件"""
        return self.where(column != value)

    def gt_(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """大于条件"""
        return self.where(column > value)

    def lt_(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """小于条件"""
        return self.where(column < value)

    def ge_(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """大于等于条件"""
        return self.where(column >= value)

    def le_(self, column: InstrumentedAttribute, value: Any) -> "BaseBuilder":
        """小于等于条件"""
        return self.where(column <= value)

    def in_(self, column: InstrumentedAttribute, values: list | tuple) -> "BaseBuilder":
        """包含于列表条件"""
        if len(values) == 1:
            return self.where(column == values[0])

        return self.where(column.in_(values))

    def like(self, column: InstrumentedAttribute, pattern: str) -> "BaseBuilder":
        """模糊匹配条件"""
        return self.where(column.like(f"%{pattern}%"))

    def ilike(self, column: InstrumentedAttribute, pattern: str) -> "BaseBuilder":
        """忽略大小写的模糊匹配条件"""
        return self.where(column.ilike(f"%{pattern}%"))

    def is_null(self, column: InstrumentedAttribute) -> "BaseBuilder":
        """为空检查条件"""
        return self.where(column.is_(None))

    def between_(self, column: InstrumentedAttribute, start_value: Any, end_value: Any) -> "BaseBuilder":
        """范围查询条件"""
        return self.where(column.between(start_value, end_value))

    def contains_(self, column: InstrumentedAttribute, values: list) -> "BaseBuilder":
        return self.where(column.contains(values))

    def or_(self, *conditions: tuple[BinaryExpression]) -> "BaseBuilder":
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

    def distinct_(self, *cols: InstrumentedAttribute) -> "BaseBuilder":
        """
        添加 DISTINCT 或 DISTINCT ON 条件到查询语句中

        支持两种使用方式：
            2. .distinct(Model.name) -> PostgreSQL 的 DISTINCT ON 去重

        Args:
            cols: 要去重的列（可选，仅适用于 PostgreSQL）

        Returns:
            QueryBuilder: 自身实例，支持链式调用
        """

        # 使用 PostgreSQL 的 DISTINCT ON
        self._stmt = self._stmt.distinct(*cols)
        return self

    def group_by_(self, *cols: InstrumentedAttribute) -> "BaseBuilder":
        """
        添加 GROUP BY 子句到查询语句中

        Args:
            cols: 要分组的列（可以是多个）

        Returns:
            QueryBuilder: 自身实例，支持链式调用
        """
        if not cols:
            return self

        self._stmt = self._stmt.group_by(*cols)
        return self

    def desc_(self, col: InstrumentedAttribute) -> "BaseBuilder":
        self._stmt = self._stmt.order_by(col.desc())
        return self

    def asc_(self, col: InstrumentedAttribute) -> "BaseBuilder":
        self._stmt = self._stmt.order_by(col.asc())
        return self

    def _apply_delete_at_is_none(self) -> None:
        """安全地添加软删除过滤条件"""
        deleted_column = self._model_cls.get_column_or_none(self._model_cls.deleted_at_column_name())
        self._stmt = self._stmt.where(deleted_column.is_(None))

    def where(self, *conditions: ClauseElement) -> "BaseBuilder":
        """
        example:
        builder = QueryBuilder(MyModel)
        builder.where_v1(MyModel.id == 1, MyModel.name == "Alice")
        stmt = builder.stmt  # SELECT * FROM my_model WHERE id = 1 AND name = "Alice"

        example:
        filters = [MyModel.id == 1, MyModel.name == "Alice"]
        builder.where_v1(*filters)
        """
        if not conditions:
            return self

        self._stmt = self._stmt.where(*conditions)
        return self


class QueryBuilder(BaseBuilder):

    def __init__(
            self,
            model_cls: type[ModelMixin],
            *,
            include_deleted: bool | None = None,
            initial_where: ColumnExpressionArgument | None = None,
            custom_stmt: Select | None = None,

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

        if custom_stmt is not None:
            self._stmt: Select = custom_stmt
        else:
            # 基础查询语句
            self._stmt: Select = select(self._model_cls)

            # 默认过滤已删除记录
            if include_deleted is False and self._model_cls.has_deleted_at_column:
                self._apply_delete_at_is_none()

            # 添加初始WHERE条件
            if initial_where is not None:
                self._stmt = self._stmt.where(initial_where)

    @property
    def select_stmt(self) -> Select:
        return self._stmt

    @property
    def subquery_stmt(self) -> Subquery:
        return self._stmt.subquery()

    async def all(self, *, include_deleted: bool | None = None) -> list[MixinModelType]:
        if include_deleted is False and self._model_cls.has_deleted_at_column:
            self._apply_delete_at_is_none()

        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalars().all()
            except Exception as e:
                raise Exception(f"{self._model_cls.__name__} all error: {e}") from e
        return data

    async def first(self, *, include_deleted: bool | None = None) -> MixinModelType | None:
        if include_deleted is False and self._model_cls.has_deleted_at_column:
            self._apply_delete_at_is_none()

        async with get_session() as sess:
            try:
                result = await sess.execute(self._stmt)
                data = result.scalars().first()
            except Exception as e:
                raise Exception(f"{self._model_cls.__name__} scalar_one_or_none error: {e}") from e
        return data

    async def get_or_none(self, *, include_deleted: bool | None = None) -> MixinModelType | None:
        return await self.first(include_deleted=include_deleted)

    async def get_or_exec(self, *, include_deleted: bool | None = None) -> MixinModelType | None:
        data = await self.get_or_none(include_deleted=include_deleted)
        if not data:
            raise Exception(f"{self._model_cls.__name__} get_or_exec not found")
        return data

    def paginate(self, *, page: int | None = None, limit: int | None = None) -> "QueryBuilder":
        if page and limit:
            self._stmt = self._stmt.offset((page - 1) * limit).limit(limit)
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        self._stmt = self._stmt.limit(limit)
        return self


class CountBuilder(BaseBuilder):
    def __init__(
            self,
            model_cls: type[ModelMixin],
            *,
            count_column: InstrumentedAttribute = None,
            is_distinct: bool = False,
            include_deleted: bool = None
    ):
        """
        计数查询构建器

        参数:
            model_class: 要计数的模型类
            count_column: 要计数的列（默认为主键ID）
            include_deleted: 是否包含已软删除的记录（默认False）
        """
        super().__init__(model_cls)

        # 设置计数列（默认为主键）
        count_column: InstrumentedAttribute = count_column if count_column is not None else self._model_cls.id

        if is_distinct:
            expression: Function[Column] = func.count(distinct(count_column))
        else:
            expression: Function[Column] = func.count(count_column)

        # 构建基础查询
        self._stmt: Select = select(expression)

        # 默认过滤已删除记录
        if include_deleted is False and self._model_cls.has_deleted_at_column():
            self._apply_delete_at_is_none()

    @property
    def count_stmt(self) -> Select:
        return self._stmt

    async def count(self) -> int:
        async with get_session() as sess:
            try:
                exec_result = await sess.execute(self._stmt)
                data = exec_result.scalar()
            except Exception as e:
                raise Exception(f"{self._model_cls.__name__} count error: {e}") from e
        return data


class UpdateBuilder(BaseBuilder):
    def __init__(
            self,
            *,
            model_cls: type[ModelMixin] | None = None,
            model_ins: ModelMixin | None = None
    ):
        """
        更新构建器初始化

        参数:
            model_class: 要更新的模型类（用于批量更新）
            model_instance: 要更新的模型实例（用于单条记录更新）

        注意:
            - 必须且只能提供 model_class 或 model_instance 中的一个
            - 如果提供 model_instance，会自动添加 WHERE id=instance.id 条件
        """
        # 参数校验
        if (model_cls is None) == (model_ins is None):
            raise Exception("must and can only provide one of model_class or model_instance")

        # 调用父类初始化
        super().__init__(model_cls if model_cls is not None else model_ins.__class__)

        # 初始化更新语句
        self._stmt: Update = update(self._model_cls)
        self._update_dict = {}

        # 如果是实例更新，添加ID条件
        if model_ins is not None:
            model_id_column: InstrumentedAttribute = self._model_cls.get_column_or_none("id")
            self._stmt = self._stmt.where(model_id_column == model_ins.id)

    def update(self, **kwargs) -> "UpdateBuilder":
        if not kwargs:
            return self

        for column_name, value in kwargs.items():
            if not self._model_cls.has_column(column_name):
                continue

            if isinstance(value, datetime) and value.tzinfo is not None:
                value = value.replace(tzinfo=None)

            self._update_dict[column_name] = value

        return self

    def soft_delete(self):
        if not self._model_cls.has_deleted_at_column():
            return self

        self._update_dict[self._model_cls.deleted_at_column_name()] = get_utc_without_tzinfo()
        return self

    @property
    def update_stmt(self) -> Update:
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
        current_time = get_utc_without_tzinfo()

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

        user_id = get_user_id_context_var()
        # 如果模型支持更新人字段，自动设置当前用户ID
        if self._model_cls.has_updater_id_column():
            self._update_dict.setdefault(
                self._model_cls.updater_id_column_name(),
                user_id  # 从上下文获取当前用户ID
            )

        # 将更新字典应用到SQL语句
        self._stmt = self._stmt.values(**self._update_dict).execution_options(synchronize_session=False)

        return self._stmt

    async def execute(self):
        if not self._update_dict:
            logger.warning(f"{self._model_cls.__name__} no update data")
            return

        async with get_session() as sess:
            try:
                await sess.execute(self.update_stmt)
                await sess.commit()
            except Exception as e:
                raise Exception(f"{self._model_cls.__name__} execute update_stmt failed: {e}") from e


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
            model_cls: type[ModelMixin] | None = None,
            model_ins: ModelMixin | None = None
    ):
        """
        删除构建器初始化

        参数:
            model_class: 要删除的模型类（用于批量删除）
            model_instance: 要删除的模型实例（用于单条记录删除）

        注意:
            - 必须且只能提供 model_class 或 model_instance 中的一个
            - 如果提供 model_instance，会自动添加 WHERE id=instance.id 条件
        """
        # 参数校验
        if (model_cls is None) == (model_ins is None):
            raise Exception("must and can only provide one of model_class or model_instance")

        # 调用父类初始化
        super().__init__(model_cls if model_cls is not None else model_ins.__class__)

        # 初始化删除语句
        self._stmt: Delete = delete(self._model_cls)

        # 如果是实例删除，添加ID条件
        if model_ins is not None:
            model_id_column: InstrumentedAttribute = self._model_cls.get_column_or_none("id")
            self._stmt = self._stmt.where(model_id_column == model_ins.id)

    @property
    def delete_stmt(self) -> Delete:
        """获取最终的删除语句（带属性访问器）"""
        return self._stmt

    async def execute(self) -> int:
        """执行删除操作

        返回:
            删除的记录数

        异常:
            Exception: 当删除操作失败时抛出
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
                raise Exception(f"{self._model_cls.__name__} delete error: {traceback.format_exc()}") from e


def _validate_model_cls(model_cls: type | None, expected_type: type = type, subclass_of: type = ModelMixin):
    """校验 model_cls 是否为指定的类型且是指定类的子类"""
    if model_cls is None:
        raise Exception("model_cls cannot be None")

    if not isinstance(model_cls, expected_type):
        raise Exception(
            f"model_cls must be a {expected_type.__name__}, got {type(model_cls).__name__}"
        )

    if not issubclass(model_cls, subclass_of):
        raise Exception(
            f"model_cls must be a subclass of {subclass_of.__name__}, got {model_cls.__name__}"
        )


def _validate_model_ins(model_ins: object, expected_type: type = ModelMixin):
    """校验 model_ins 是否为指定的类型且不是 None"""
    if model_ins is None:
        raise Exception("model_ins cannot be None")

    if not isinstance(model_ins, expected_type):
        raise Exception(
            f"model_ins must be a {expected_type.__name__} instance, got {type(model_ins).__name__}"
        )


def new_cls_querier(
        model_cls: type[ModelMixin],
        *,
        include_deleted: bool | None = None,
        initial_where: ColumnExpressionArgument | None = None
) -> QueryBuilder:
    """创建一个新的查询器实例

    参数:
        model_cls: 要查询的模型类

    返回:
        查询器实例
    """
    _validate_model_cls(model_cls)
    return QueryBuilder(model_cls=model_cls, include_deleted=include_deleted, initial_where=initial_where)


def new_sub_querier(
        model_cls: type[ModelMixin],
        *,
        subquery: Subquery,
        include_deleted: bool | None = None,
        initial_where: ColumnExpressionArgument | None = None
) -> QueryBuilder:
    """创建一个新的子查询器实例

    参数:
        model_cls: 要查询的模型类
        sub_stmt: 子查询语句

    返回:
        查询器实例
    """
    _validate_model_cls(model_cls)
    alias = aliased(model_cls, subquery)
    return QueryBuilder(
        model_cls=model_cls,
        include_deleted=include_deleted,
        initial_where=initial_where,
        custom_stmt=select(alias)
    )


def new_custom_querier(
        model_cls: type[ModelMixin],
        *,
        custom_stmt: Select,
        include_deleted: bool | None = None,
        initial_where: ColumnExpressionArgument | None = None
) -> QueryBuilder:
    """创建一个新的自定义查询器实例

    参数:
        model_cls: 要查询的模型类
        custom_stmt: 自定义查询语句

    返回:
        查询器实例
    """
    _validate_model_cls(model_cls)
    return QueryBuilder(
        model_cls=model_cls,
        include_deleted=include_deleted,
        initial_where=initial_where,
        custom_stmt=custom_stmt
    )


def new_cls_updater(model_cls: type[ModelMixin]) -> UpdateBuilder:
    """创建一个基于模型类的更新器

    Args:
        model_cls: 必须是 ModelMixin 的子类（不是实例）

    Raises:
        Exception: 当输入无效时返回500错误

    Returns:
        UpdateBuilder: 更新器实例
    """
    _validate_model_cls(model_cls)
    return UpdateBuilder(model_cls=model_cls)


def new_ins_updater(model_ins: ModelMixin) -> UpdateBuilder:
    """创建一个基于模型实例的更新器

    Args:
        model_ins: 必须是 ModelMixin 的非空实例

    Raises:
        Exception: 当输入无效时返回500错误

    Returns:
        UpdateBuilder: 更新器实例
    """
    _validate_model_ins(model_ins)
    return UpdateBuilder(model_ins=model_ins)


def new_deleter(model_cls: type[ModelMixin]) -> DeleteBuilder:
    """创建一个新的删除器实例

    参数:
        model_cls: 要删除的模型类

    返回:
        删除器实例
    """
    _validate_model_cls(model_cls)
    return DeleteBuilder(model_cls=model_cls)


def new_ins_deleter(model_ins: ModelMixin) -> DeleteBuilder:
    """创建一个基于模型实例的删除器

    Args:
        model_ins: 必须是 ModelMixin 的非空实例

    Raises:
        Exception: 当输入无效时返回500错误

    Returns:
        DeleteBuilder: 删除器实例
    """
    _validate_model_ins(model_ins)
    return DeleteBuilder(model_ins=model_ins)


def new_counter(
        model_cls: type[ModelMixin],
        *,
        include_deleted: bool | None = None
) -> CountBuilder:
    """创建一个新的计数器实例

    参数:
        model_cls: 要计数的模型类

    返回:
        计数器实例
    """
    _validate_model_cls(model_cls)
    return CountBuilder(model_cls=model_cls, include_deleted=include_deleted)


def new_col_counter(
        model_cls: type[ModelMixin],
        *,
        count_column: InstrumentedAttribute,
        is_distinct: bool = False,
        include_deleted: bool | None = None
) -> CountBuilder:
    """创建一个新的计数器实例，针对特定的列

    参数:
        model_cls: 要计数的模型类
        column_name: 要计数的列名

    返回:
        计数器实例
    """
    _validate_model_cls(model_cls)
    return CountBuilder(
        model_cls=model_cls, count_column=count_column, include_deleted=include_deleted, is_distinct=is_distinct
    )


class BaseORMHelper:
    """[DEPRECATED] This class is deprecated and will be removed in future versions."""

    def __init__(self):
        pass

    @classmethod
    def querier(cls, model_cls: type[ModelMixin]):
        return new_cls_querier(model_cls, include_deleted=False)

    @classmethod
    def querier_include_deleted(cls, model_cls: type[ModelMixin]):
        return new_cls_querier(model_cls=model_cls, include_deleted=True)

    @classmethod
    def updater(cls, *, model_cls: type[ModelMixin] = None, model_ins: ModelMixin = None):
        if (model_cls is None) == (model_ins is None):
            raise Exception("must and can only provide one of model_class or model_instance")

        if model_cls:
            return cls.cls_updater(model_cls=model_cls)
        else:
            return cls.ins_updater(model_ins=model_ins)

    @classmethod
    def cls_updater(cls, model_cls: type[ModelMixin]):
        return new_cls_updater(model_cls=model_cls)

    @classmethod
    def ins_updater(cls, model_ins: ModelMixin):
        return new_ins_updater(model_ins=model_ins)

    @classmethod
    def counter(cls, model_cls: type[ModelMixin]):
        return new_counter(model_cls)

    @classmethod
    def deleter(cls, *, model_cls: type[ModelMixin] = None):
        return new_deleter(model_cls=model_cls)
