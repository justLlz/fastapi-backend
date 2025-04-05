from fastapi import APIRouter, Request

from internal.services.user import user_srv
from pkg.resp_helper import response_factory

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/hello_world")
async def hello_world(request: Request):
    await user_srv.hello(request)
    return response_factory.resp_200()
