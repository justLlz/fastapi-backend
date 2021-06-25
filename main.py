from fastapi import FastAPI, Query, Depends, Path
from routers.index import index_router
from routers.user import user_router

app = FastAPI(debug=True)
app.include_router(index_router)
app.include_router(user_router)


@app.get('/')
async def func_hello():
    return {"hello": "world"}


@app.get('/student/{s_id}')
async def student_info(s_id: int):
    return {'name': 'llz', 'age': 26, 's_id': s_id}


if __name__ == '__main__':
    pass
