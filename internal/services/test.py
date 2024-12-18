from fastapi import Request
from fastapi.responses import ORJSONResponse

from pkg.resp import resp_200


class TestService:
    @staticmethod
    async def hello_world(request: Request) -> ORJSONResponse:
        return resp_200(data={"msg": "hello world"})
