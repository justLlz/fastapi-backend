from fastapi import APIRouter

router = APIRouter(prefix="/v1/public")
from internal.controllers.publicapi import test

router.include_router(test.router)
