from typing import Type, Union

from internal.utils.orm_helpers import QueryBuilder, UpdateBuilder, CountBuilder, DeleteBuilder
from internal.utils.cache_helpers import cache
from internal.models import ModelMixin


class BaseService:
    cache = cache

    @classmethod
    def querier(cls, model: Type[ModelMixin]):
        return QueryBuilder(model)

    @classmethod
    def updater(cls, model_class: Type[ModelMixin] = None, model_instance: ModelMixin = None):
        return UpdateBuilder(model_cls=model_class, model_instance=model_instance)

    @classmethod
    def counter(cls, model: Type[ModelMixin]):
        return CountBuilder(model)

    @classmethod
    def deleter(cls, model_class: Type[ModelMixin] = None, model_instance: ModelMixin = None):
        return DeleteBuilder(model_cls=model_class, model_instance=model_instance)
