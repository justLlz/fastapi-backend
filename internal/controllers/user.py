from fastapi import APIRouter, Query, Request
from typing import Annotated
from internal.services.user import user_srv

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/hello_world")
async def hello_world(request: Request):
    return await user_srv.hello(request)


@router.get("/get_user_list")
async def get_user_list(request: Request,
                        page: Annotated[int, Query(ge=1, le=1000)] = 1,
                        limit: Annotated[int, Query(ge=1, le=1000)] = 10):
    return await user_srv.get_user_list(request, page, limit)
