from fastapi import APIRouter, Depends
from pydantic import BaseModel

from settings import get_setting
from utils.logger import logger

router = APIRouter()


class SettingInfo(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None


@router.get('/setting/info')
async def get_setting_info(setting_info=Depends(get_setting)):
    logger.error('kky')
    return {'app_name': f'{setting_info.PROJECT_NAME}'}


"""
(1)、如果这个参数已经在路径中被声明过，那么它就是一个路径参数。

(2)、如果这个参数的类型是单类型的(如str、float、int、bool等)，那么它就是一个请求参数。

(3)、如果这个参数的类型是Pydantic数据模型，那么它就被认为是Request Body参数。
"""


@router.post('/setting/{setting_type}/info')
async def add_setting(setting_type: str, setting_info: SettingInfo):
    request_body_data = setting_info.dict()
    return {"setting_type": setting_type}


@router.get('/student/{s_id}')
async def student_info(s_id: int):
    return {'name': 'llz', 'age': 26, 's_id': s_id}
