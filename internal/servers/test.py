from fastapi import APIRouter, Request

from internal.services.test import TestService

router = APIRouter(prefix="", tags=["test"])


@router.get("/hello_world")
async def hello_world(request: Request):
    return TestService.hello_world(request)
