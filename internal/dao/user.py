from internal.dao import BaseDao
from internal.models.user import User


class UserDao(BaseDao):

    async def get_user_by_phone(self, phone: str) -> User:
        return await self.querier(User).where(User.phone == phone).get_or_none()


user_dao = UserDao()
