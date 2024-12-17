from typing import Type, Union

from internal.core.bcrypt import verify_password
from internal.dao import QueryBuilder
from internal.models.user import ManageUser, User


async def auth_by_account(user_model_class: Union[Type[ManageUser], Type[User]],
                          account: str, password: str) -> (Union[ManageUser, User], bool):
    # 查询数据库，根据用户名获取用户信息
    user: Union[ManageUser, User] = await (QueryBuilder(user_model_class).
                                           where(user_model_class.account, account).get_or_exec())

    # 验证密码
    if not verify_password(password, user.password):
        return None, False

    return user, True


async def auth_by_phone(phone: str) -> (User, bool):
    user: User = await (QueryBuilder(User).where(User.phone, phone).get_or_exec())
    return user, True
