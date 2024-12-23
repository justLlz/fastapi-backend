from typing import Optional

from fastapi import Request
from fastapi.responses import ORJSONResponse

from internal.core.bcrypt import verify_password
from internal.models.user import ManageUser, User
from internal.services import BaseService
from pkg.resp import resp_401


class AuthService(BaseService):
    """
    认证服务
    """

    @classmethod
    async def backend_user_login(
            cls, _: Request, account: str, password: str) -> (str, Optional[ORJSONResponse]):
        """
        用户名密码登录
        """
        user: ManageUser = await (cls.querier(ManageUser).where_(ManageUser.account, account).get_or_exec())
        if not verify_password(password, user.password):
            return "", resp_401(message="wrong account or password")

        session = await cls.cache.login_and_set_session(user.to_dict())
        return session, None

    @classmethod
    async def frontend_user_login_or_create(cls, _: Request, phone: str) -> dict:
        user: User = await (cls.querier(User).where_(User.phone, phone).get_or_none())
        if not user:
            user = User.init_by_phone(phone)
            await user.save()

        session = await cls.cache.login_and_set_session(user.to_dict())
        return {"session": session}
