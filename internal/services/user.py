from fastapi import Request
from fastapi.responses import ORJSONResponse
from starlette.status import HTTP_400_BAD_REQUEST

import pkg
from internal.models.user import User
from internal.services import BaseService
from pkg.resp import resp_failed, resp_success


class UserService(BaseService):

    async def create_by_phone(self, _: Request, phone: str) -> ORJSONResponse:
        user = await self.querier(User).where_v1(User.phone, phone).get_or_none()
        if user:
            return resp_failed(HTTP_400_BAD_REQUEST, message="phone already exists")

        user = User.init_by_phone(phone)
        await user.save()
        return resp_success()

    async def get_user_by_id(self, _: Request, user_id: int) -> User:
        user = await self.querier(User).where_v1(User.id, user_id).get_or_exec()
        return user

    async def update_user(self, request: Request, user_ins: User, update_dict: dict) -> User:
        change_dict = {}
        cols = user_ins.__mapper__.c.keys()
        for k, new_val in update_dict.items():
            if k not in cols:
                continue

            if (old_val := getattr(user_ins, k)) != new_val:
                change_dict[k] = [old_val, new_val]
                setattr(user_ins, k, new_val)

        await self.updater(user_ins).update(**change_dict).execute()

        session = ""
        # 更新缓存
        user = await self.get_user_by_id(request, user_ins.id)
        await self.cache.set_session(session, user.to_dict())

        user = await self.get_user_by_id(request, user_ins.id)
        return user

    async def delete_user(self, _: Request, user_id: int) -> None:
        user_ins = await self.querier(User).where_v1(User.id, user_id).get_or_exec()
        await self.updater(user_ins).values(deleted_at=pkg.get_utc_datetime()).execute()


user_srv = UserService()
