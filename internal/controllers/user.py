from fastapi import APIRouter, Query, Request
from typing import Annotated
from internal.services.user import user_srv
from pkg.resp import response_factory

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/hello_world")
async def hello_world(request: Request):
    await user_srv.hello(request)
    return response_factory.resp_200()


@router.get("/test_querier")
async def get_user_list(request: Request,
                        page: Annotated[int, Query(ge=1, le=1000)] = 1,
                        limit: Annotated[int, Query(ge=1, le=1000)] = 10):
    data = await user_srv.querier_test(request, page, limit)
    return response_factory.resp_list(data=[i.to_dict() for i in data], page=page, limit=limit, total=100)
