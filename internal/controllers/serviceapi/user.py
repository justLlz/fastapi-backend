from fastapi import Request, APIRouter

from pkg.resp_helper import response_factory

router = APIRouter(prefix="/user", tags=["service v1 user"])


@router.get("", summary="service hello world")
def hello_world(request: Request):
    return response_factory.resp_200()
