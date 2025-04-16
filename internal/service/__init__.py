from typing import Type, Union

from internal.utils.orm_helpers import (QueryBuilder, UpdateBuilder, CountBuilder, DeleteBuilder, new_cls_updater,
                                        new_ins_updater, new_querier_by_cls)
from internal.utils.cache_helpers import cache
from internal.models import ModelMixin


class BaseService:

    @classmethod
    def querier(cls, model: Type[ModelMixin]):
        return new_querier_by_cls(model)

    @classmethod
    def updater(cls, model_cls: Type[ModelMixin]):
        return new_cls_updater(model_cls)

    @classmethod
    def ins_updater(cls, model_instance: ModelMixin):
        return new_ins_updater(model_instance)

    @classmethod
    def counter(cls, model: Type[ModelMixin]):
        return CountBuilder(model)

    @classmethod
    def deleter(cls, model_cls: Type[ModelMixin] = None, model_instance: ModelMixin = None):
        return DeleteBuilder(model_cls=model_cls, model_instance=model_instance)

    @property
    def cache(self):
        return cache
