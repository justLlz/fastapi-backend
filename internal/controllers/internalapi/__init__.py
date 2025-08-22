from fastapi import APIRouter

router = APIRouter(prefix="/v1/internal")
from internal.controllers.internalapi import user

router.include_router(user.router)
