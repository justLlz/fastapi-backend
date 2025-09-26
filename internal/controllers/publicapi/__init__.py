from fastapi import APIRouter
from internal.controllers.publicapi import test

router = APIRouter(prefix="/v1/public")

routers = [
    test.router
]

for r in routers:
    router.include_router(r)
