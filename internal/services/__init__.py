from typing import Type, Union

from internal import dao
from internal.dao.cache import Cache
from internal.models import MixinModel


class BaseService:
    cache = Cache()

    @classmethod
    def querier(cls, model: Type[MixinModel]):
        return dao.QueryBuilder(model)

    @classmethod
    def updater(cls, model: Union[Type[MixinModel], MixinModel]):
        return dao.UpdateBuilder(model)

    @classmethod
    def counter(cls, model: Type[MixinModel]):
        return dao.CountBuilder(model)
