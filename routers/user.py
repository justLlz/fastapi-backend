from fastapi import APIRouter

user_router = APIRouter()


@user_router.get('/user/{user_id}', tags=["users"])
async def user_info():
    return [{"username": "Foo"}, {"username": "Bar"}]


@user_router.get("/user/me", tags=["users"])
async def read_user_me():
    return {"username": "fakecurrentuser"}


@user_router.get("/user/{username}", tags=["users"])
async def read_user(username: str):
    return {"username": username}
