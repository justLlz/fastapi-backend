"""
该目录主要用于数据库操作
"""
from sqlalchemy import Subquery
from sqlalchemy.orm import InstrumentedAttribute

from internal.models import ModelMixin
from internal.utils.exception import AppException
from internal.utils.mixin_type import MixinModelType
from internal.utils.orm_helpers import (CountBuilder, QueryBuilder, UpdateBuilder, new_cls_querier,
                                        new_cls_updater,
                                        new_col_counter, new_counter,
                                        new_ins_updater, new_sub_querier)
from pkg.logger_tool import logger


class BaseDao:
    _model_cls: type[ModelMixin] = None

    @property
    def model_cls(self) -> type[ModelMixin]:
        return self._model_cls

    def create(self, **kwargs) -> MixinModelType:
        return self._model_cls.create(**kwargs)

    @property
    def querier(self) -> QueryBuilder:
        return new_cls_querier(self._model_cls, include_deleted=False).desc_(self._model_cls.updated_at)

    @property
    def querier_inc_deleted(self) -> QueryBuilder:
        return new_cls_querier(self._model_cls, include_deleted=True).desc_(self._model_cls.updated_at)

    @property
    def querier_unsorted(self) -> QueryBuilder:
        return new_cls_querier(self._model_cls, include_deleted=False)

    @staticmethod
    def querier_inc_deleted_unsorted(self) -> QueryBuilder:
        return new_cls_querier(self._model_cls, include_deleted=True)

    def sub_querier(self, subquery: Subquery) -> QueryBuilder:
        return new_sub_querier(self._model_cls, subquery=subquery)

    @property
    def counter(self) -> CountBuilder:
        return new_counter(self._model_cls, include_deleted=False)

    @property
    def counter_inc_deleted(self) -> CountBuilder:
        return new_counter(self._model_cls, include_deleted=True)

    def col_counter(self, count_column: InstrumentedAttribute, *, is_distinct: bool = False) -> CountBuilder:
        return new_col_counter(
            self._model_cls, count_column=count_column, is_distinct=is_distinct, include_deleted=False
        )

    @property
    def updater(self) -> UpdateBuilder:
        return new_cls_updater(self._model_cls)

    @staticmethod
    def ins_updater(ins: ModelMixin) -> UpdateBuilder:
        return new_ins_updater(ins)

    async def query_by_id_or_none(
            self,
            primary_id: int,
            *,
            creator_id: int = None,
            include_deleted: bool = False
    ) -> MixinModelType:
        if include_deleted:
            querier = self.querier_inc_deleted.eq_(self._model_cls.id, primary_id)
        else:
            querier = self.querier.eq_(self._model_cls.id, primary_id)

        if creator_id and self._model_cls.has_creator_id_column():
            querier = self.querier.where(
                self._model_cls.get_creator_id_column() == creator_id
            )

        return await querier.first(include_deleted=include_deleted)

    async def query_by_id_or_exec(
            self,
            primary_id: int,
            *,
            creator_id: int = None,
            include_deleted: bool = False
    ) -> MixinModelType:
        ins = await self.query_by_id_or_none(primary_id, creator_id=creator_id, include_deleted=include_deleted)
        if not ins:
            logger.error(f"{self._model_cls.__name__} not found for oid={primary_id}")
            raise AppException(code=404, detail=f"{self._model_cls.__name__} not found")
        return ins

    async def query_by_ids(self, ids: list[int]) -> list[MixinModelType]:
        return await self.querier.in_(self._model_cls.id, ids).all()
