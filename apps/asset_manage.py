from fastapi import APIRouter, Query
from typing import Annotated

from entity.device import DeviceEntity
from models.device import Device
from schemas.device import DeviceCreate
from utils.response_code import resp_200

router = APIRouter()


# 查询设备
@router.get("/device", tags=["device"], description='查询设备列表')
async def device_lst(page: Annotated[int, Query(..., gt=0)] = 0, limit: Annotated[int, Query(..., gt=0)] = 10):
    return resp_200(data={'page': page, 'limit': limit})


# 新增设备
@router.post("/device", tags=["device"], description='增加设备')
async def device_add(device: DeviceCreate):
    dev = Device.create(device)
    await dev.save()

    data = DeviceEntity.model_to_dict(dev)
    return resp_200(data=data)


# 查询单个设备
@router.get("/device/{record_id}", tags=["device"], description='查询单个设备')
async def device_get(record_id: int):
    return resp_200(data={'id': record_id})


# 编辑设备
@router.put("/device/{record_id}", tags=["device"], description='编辑设备')
async def device_update(record_id: int):
    """
    Edit a single device by record_id
    """
    return resp_200(data={'record_id': record_id})


# 删除设备
@router.delete("/device/{record_id}", tags=["device"], description='删除设备')
async def device_delete(record_id: int):
    return resp_200(data={'record_id': record_id})
