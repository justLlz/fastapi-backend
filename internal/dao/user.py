from internal.dao import BaseDao
from internal.models.user import User


class UserDao(BaseDao):
    _model_cls: type[User] = User

    async def get_user_by_phone(self, phone: str) -> User:
        return await self.querier.where(self._model_cls.phone == phone).first()


user_dao = UserDao()
