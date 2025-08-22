from fastapi import APIRouter

router = APIRouter(prefix="/v1")
from internal.controllers.web import user

router.include_router(user.router)
