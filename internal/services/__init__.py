from typing import Type, Union

from internal import dao
from internal.dao.cache import Cache
from internal.models.mixin import ModelMixin


class BaseService:
    cache = Cache()

    @classmethod
    def querier(cls, model: Type[ModelMixin]):
        return dao.QueryBuilder(model)

    @classmethod
    def updater(cls, model: Union[Type[ModelMixin], ModelMixin]):
        return dao.UpdateBuilder(model)

    @classmethod
    def counter(cls, model: Type[ModelMixin]):
        return dao.CountBuilder(model)
