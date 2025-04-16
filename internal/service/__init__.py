from http.client import HTTPException
from typing import Type, Union

from internal.utils.orm_helpers import (_QueryBuilder, _UpdateBuilder, _CountBuilder, _DeleteBuilder, new_cls_updater,
                                        new_counter, new_deleter, new_ins_updater, new_cls_querier)
from internal.utils.cache_helpers import cache
from internal.models import ModelMixin


class BaseService:

    @classmethod
    def querier(cls, model_cls: Type[ModelMixin]):
        return new_cls_querier(model_cls)

    @classmethod
    def updater(cls, *, model_cls: Type[ModelMixin] = None, model_ins: ModelMixin = None):
        if (model_cls is None) == (model_ins is None):
            raise HTTPException(500, "must and can only provide one of model_class or model_instance")

        if model_cls:
            return cls.cls_updater(model_cls=model_cls)

        if model_ins:
            return cls.ins_updater(model_ins=model_ins)

    @classmethod
    def cls_updater(cls, model_cls: Type[ModelMixin]):
        return new_cls_updater(model_cls=model_cls)

    @classmethod
    def ins_updater(cls, model_ins: ModelMixin):
        return new_ins_updater(model_ins=model_ins)

    @classmethod
    def counter(cls, model_cls: Type[ModelMixin]):
        return new_counter(model_cls)

    @classmethod
    def deleter(cls, *, model_cls: Type[ModelMixin] = None):
        return new_deleter(model_cls=model_cls)

    @property
    def cache(self):
        return cache
