from decimal import Decimal
from typing import Annotated, TypeVar, Union

from pydantic import AfterValidator, Field

from internal.models import ModelMixin
from pkg import validate_phone_number

MixinValType = Union[list, set, tuple, frozenset, str, int, float, bool, Decimal, None]
MixinModelType = TypeVar("MixinModelType", bound=ModelMixin)  # 定义一个泛型变量 T，继承自 ModelMixin


def validate_phone(value):
    # 校验手机号格式
    if not validate_phone_number(value):
        raise ValueError('Invalid phone number format')
    return value


MixinPhoneType = Annotated[str, Field(...), AfterValidator(validate_phone)]


def validate_email(value):
    # 校验邮箱格式
    if '@' not in value:
        raise ValueError('Invalid email format')
    return value


MixinEmailType = Annotated[str, Field(...), AfterValidator(validate_email)]
