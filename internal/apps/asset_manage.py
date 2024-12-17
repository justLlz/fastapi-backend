from fastapi import APIRouter, Query, Body
from typing import Annotated

from dao.device import DeviceDao
from internal.entity import AssetStatus
from internal.entity import DeviceEntity, DeviceCreate
from models.device import Device
from utils.response_utils import resp_200

router = APIRouter()


# 查询设备
@router.get("/device", tags=["device"], description='查询设备列表')
async def device_lst(asset_status: Annotated[AssetStatus, Query(..., )],
                     page: Annotated[int, Query(..., gt=0)] = 1,
                     limit: Annotated[int, Query(..., gt=0)] = 10,
                     ):
    m_lst = await DeviceDao.get_device_batch(page, limit, asset_status)
    resp_data = DeviceEntity.batch_model_to_dict(m_lst)
    return resp_200(data=resp_data)


# 新增设备
@router.post("/device", tags=["device"], description='增加设备')
async def device_add(device: Annotated[DeviceCreate, Body(...)]):
    dev = Device.create(device)
    await dev.save()

    return resp_200()


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
