from typing import List

from pydantic import BaseModel, ValidationError, validator, EmailStr, validate_email

"""
https://pydantic-docs.helpmanual.io/usage/validators/
"""


class UserModel(BaseModel):
    name: str
    username: str
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

    @validator('names', each_item=True)
    def check_names_not_empty(cls, v):
        """检查没一项 list set, 如果和父类检查相同的字段，则不会运行"""
        assert v != '', 'Empty strings are not allowed.'
        return v


if __name__ == '__main__':
    pass
