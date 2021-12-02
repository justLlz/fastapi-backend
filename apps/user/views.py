from typing import Optional

from fastapi import APIRouter, Depends
from starlette.background import BackgroundTasks

router = APIRouter()


@router.get('/user/{user_id}', tags=["users"])
async def user_info():
    return [{"username": "Foo"}, {"username": "Bar"}]


@router.get("/user/me", tags=["users"])
async def read_user_me():
    return {"username": "fakecurrentuser"}


@router.get("/user/{username}", tags=["users"])
async def read_user(*, username: str):
    return {"username": username}


# 依赖项参数同请求参数，参数依赖项使用验证
async def common_parameters(q: Optional[str] = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


@router.get("/user/depends/items")
async def read_items(*, commons: dict = Depends(common_parameters)):
    """/user/depends/items?q=123
    {"q":"123","skip":0,"limit":100}
    """
    print(commons)
    return commons


@router.get("/background/task")
async def background_tasks():
    """后台任务"""
    BackgroundTasks.add_task()
    return {'ok': True}
