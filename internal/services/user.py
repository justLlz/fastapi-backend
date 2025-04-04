from fastapi import Request
from fastapi.responses import ORJSONResponse

import pkg
from internal.models.user import User
from internal.services import BaseService
from pkg.resp import response_factory


class UserService(BaseService):

    def querier_test(self, request: Request, page: int, limit: int) -> User:
        pass


user_srv = UserService()
