from fastapi import APIRouter, Request

from internal.services.test import TestService

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/hello_world")
async def hello_world(request: Request):
    return await TestService.hello_world(request)
