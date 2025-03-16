from fastapi import APIRouter, Request, HTTPException

from internal.services.test import TestService

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/hello_world_exception_test")
async def hello_world_exception_test(request: Request):
    # 如果触发fastapi.HTTPException会有限被main.py的exception_handler捕获，
    # 如果是Exception会被middleware的exception.py捕获
    raise HTTPException(500, "excx test")
