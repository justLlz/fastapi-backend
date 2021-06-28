from fastapi import APIRouter, Depends

router = APIRouter()


@router.get('/user/{user_id}', tags=["users"])
async def user_info():
    return [{"username": "Foo"}, {"username": "Bar"}]


@router.get("/user/me", tags=["users"])
async def read_user_me():
    return {"username": "fakecurrentuser"}


@router.get("/user/{username}", tags=["users"])
async def read_user(username: str):
    return {"username": username}
