from fastapi import APIRouter, Request

from internal.services.user import UserService

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/hello_world")
async def hello_world(request: Request):
    return await UserService.hello(request)