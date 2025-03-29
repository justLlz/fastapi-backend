from fastapi import Request
from fastapi.responses import ORJSONResponse

from pkg.resp import resp_200


class TestService:

    async def hello_world(self, request: Request) -> ORJSONResponse:
        return resp_200(data={"msg": "hello world"})


test_srv = TestService()
