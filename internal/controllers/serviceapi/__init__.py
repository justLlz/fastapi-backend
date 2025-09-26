from fastapi import APIRouter

from internal.controllers.serviceapi import user

router = APIRouter(prefix="/v1/service")

routers = [
    user.router
]

for r in routers:
    router.include_router(r)
