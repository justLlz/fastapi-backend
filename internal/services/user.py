from fastapi import HTTPException, Request
from fastapi.responses import ORJSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

import pkg
from internal.infra.db import get_session
from internal.models.user import User
from internal.services import BaseService

from pkg.logger import Logger
from pkg.resp import resp_failed, resp_success


class UserService(BaseService):

    @classmethod
    async def hello(cls, *args, **kwargs):
        return resp_success()

    @classmethod
    async def create_by_phone(cls, _: Request, phone: str) -> ORJSONResponse:
        user = await cls.querier(User).where_(User.phone, phone).get_or_none()
        if user:
            return resp_failed(HTTP_400_BAD_REQUEST, message="phone already exists")

        user = User.init_by_phone(phone)
        await user.save()
        return resp_success()

    @classmethod
    async def get_user_by_id(cls, _: Request, user_id: int) -> User:
        user = await cls.querier(User).where_(User.id, user_id).get_or_exec()
        return user

    @classmethod
    async def update_user(cls, request: Request, user_ins: User, update_dict: dict) -> User:
        change_dict = {}
        cols = user_ins.__mapper__.c.keys()
        for k, new_val in update_dict.items():
            if k not in cols:
                continue

            if (old_val := getattr(user_ins, k)) != new_val:
                change_dict[k] = [old_val, new_val]
                setattr(user_ins, k, new_val)

        try:
            async with get_session() as session:
                await session.execute(cls.updater(user_ins).values(**update_dict).stmt)
                await session.commit()
        except Exception as e:
            Logger.error(f"user_update error: {repr(e)}")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

        # 更新缓存
        user = await cls.get_user_by_id(request, user_ins.id)
        await cls.cache.set_session(session, user.to_dict())

        user = await cls.get_user_by_id(request, user_ins.id)
        return user

    @classmethod
    async def delete_user(cls, _: Request, user_id: int) -> None:
        user_ins = await cls.querier(User).where_(User.id, user_id).get_or_exec()
        await cls.updater(user_ins).values(deleted_at=pkg.get_utc_datetime()).execute()
