from pydantic import Field
from typing import Annotated

from internal.models import MixinModel


class UserReqSchema(MixinModel):
    name: Annotated[..., Field(min_length=1, max_length=20)]
