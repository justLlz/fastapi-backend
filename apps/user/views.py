from typing import Optional

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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
    """后台任务
    https://fastapi.tiangolo.com/tutorial/background-tasks/?h=backgroundtasks#using-backgroundtasks"""
    BackgroundTasks.add_task()
    return {'ok': True}


class Item(BaseModel):
    id: str
    value: str


class Message(BaseModel):
    message: str


responses = {
    404: {"description": "Item not found"},
    302: {"description": "The item was moved"},
    403: {"description": "Not enough privileges"},
}


@router.get("/test/responses/{item_id}", responses={404: {"model": Message}})
async def test_responses(*, item_id: str = Path(...)):
    """https://fastapi.tiangolo.com/advanced/additional-responses/?h=responses"""
    if item_id == "foo":
        return {"id": "foo", "value": "there goes my hero"}
    else:
        return JSONResponse(status_code=404, content={"message": "Item not found"})
