"""
该目录主要用于数据库操作
"""
from fastapi import HTTPException

from internal.models import ModelMixin
from internal.utils.orm_helpers import (CountBuilder, DeleteBuilder, QueryBuilder, UpdateBuilder, new_cls_querier,
                                        new_cls_updater,
                                        new_counter,
                                        new_deleter, new_ins_updater)


class BaseDao:
    _model_cls: type[ModelMixin] = None

    @property
    def querier(self) -> QueryBuilder:
        return new_cls_querier(self._model_cls)

    @property
    def querier_include_deleted(self) -> QueryBuilder:
        return new_cls_querier(self._model_cls, include_deleted=True)

    def sub_querier(self):

    @property
    def cls_updater(self) -> UpdateBuilder:
        return new_cls_updater(self._model_cls)

    @property
    def counter(self) -> CountBuilder:
        return new_counter(self._model_cls)

    @property
    def deleter(self) -> DeleteBuilder:
        return new_deleter(self._model_cls)

    @staticmethod
    def ins_updater(model_ins: ModelMixin):
        return new_ins_updater(model_ins=model_ins)

    @property
    def model_cls(self):
        return self._model_cls

    async def get_by_oid_or_none(self, oid: int):
        return await self.querier.eq(self._model_cls.id, oid).get_or_none()

    async def get_by_oid_or_exec(self, oid: int):
        ins = await self.get_by_oid_or_none(oid)
        if not ins:
            raise HTTPException(status_code=404, detail=f"{self._model_cls.__name__} not found for {oid}")

        return ins
