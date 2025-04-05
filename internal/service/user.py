from fastapi import Request

from internal.models.user import User
from internal.service import BaseService


class UserService(BaseService):

    def querier_test(self, request: Request, page: int, limit: int) -> User:
        pass


user_srv = UserService()
