from http.client import HTTPException
from typing import Type

from internal.models import ModelMixin
from internal.utils.cache_helpers import cache
from internal.utils.orm_helpers import (new_cls_querier, new_cls_updater, new_counter, new_deleter, new_ins_updater)


class BaseService:
    pass
