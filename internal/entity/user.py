from pydantic import BaseModel, Field
from typing import Annotated


class UserReqSchema(BaseModel):
    name: Annotated[..., Field(min_length=1, max_length=20)]
