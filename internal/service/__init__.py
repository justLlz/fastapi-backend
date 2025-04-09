from typing import Type, Union

import internal.utils.orm_helpers
from internal.utils.cache_helpers import cache
from internal.models import MixinModel


class BaseService:
    cache = cache

    @classmethod
    def querier(cls, model: Type[MixinModel]):
        return internal.utils.orm_helpers.QueryBuilder(model)

    @classmethod
    def updater(cls, model: Union[Type[MixinModel], MixinModel]):
        return internal.utils.orm_helpers.UpdateBuilder(model)

    @classmethod
    def counter(cls, model: Type[MixinModel]):
        return internal.utils.orm_helpers.CountBuilder(model)
