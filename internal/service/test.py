from fastapi import Request
from fastapi.responses import ORJSONResponse


class TestService:

    async def hello_world(self, request: Request) -> ORJSONResponse:
        return resp_200(data={"msg": "hello world"})


test_srv = TestService()
