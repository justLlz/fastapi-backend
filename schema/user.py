from typing import List, Mapping

from pydantic import BaseModel, ValidationError, validator, EmailStr, validate_email

from fastapi import Security, Body

"""
https://pydantic-docs.helpmanual.io/usage/validators/
无默认值，必须参数
有默认值，非必须参数

id: int                 必须
id: Optional[int]       必须
id: Union[int, str]     必须，字符串，数字都可以

id: int = 0             非必须，不传默认为0
id: Optional[int] = 0   非必须，不传默认为0
id: Union[int, 0]       非必须，不传默认为0

info: Mapping[str, int]

推荐加上校验(Path, Body, Query, File, Header):
    id: Optional[int] = Body(..., default=0)     必须, 不能为None
    id: Union[int, str] = Body(..., default=0)   必须, 不能为None，可以是int, str
    
    id: Optional[int] = Body(...)                必须, 不能为None
    id: Union[int, str] = Body(...)              必须, 不能为None，可以是int, str
    
Optional 是为了让 IDE 识别到该参数有一个类型提示，可以传指定的类型和 None，且参数是可选非必传的
Optional[int] 等价于 Union[int, None],既可以传指定的类型 int，也可以传 None
"""


class UserModel(BaseModel):
    name: str
    username: str
    nikename: List[str]
    password1: str
    password2: str
    emails: List[str]

    @validator('name')
    def name_must_contain_space(cls, v):
        if ' ' not in v:
            raise ValueError('must contain a space')
        return v.title()

    @validator('password2')
    def passwords_match(cls, v, values, **kwargs):
        if 'password1' in values and v != values['password1']:
            raise ValueError('passwords do not match')
        return v

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.isalnum(), 'must be alphanumeric'
        return v

    @validator('nikename', each_item=True)
    def check_names_not_empty(cls, v):
        """检查没一项 list set, 如果和父类检查相同的字段，则不会运行"""
        assert v != '', 'Empty strings are not allowed.'
        return v


if __name__ == '__main__':
    pass
