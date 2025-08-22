from fastapi import APIRouter

router = APIRouter(prefix="/v1/service")

from internal.controllers.serviceapi import user

router.include_router(user.router)
