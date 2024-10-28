from fastapi import HTTPException
from fastapi import status as http_status

from utils.db import get_session
from models.device import Device
from typing import List
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError


class DeviceDao(Device):

    # 根据 page, limit, status 批量获取设备
    @classmethod
    async def get_device_batch(cls, page: int, limit: int, asset_status: str) -> List[Device]:
        async with get_session() as session:
            try:
                stmt = (select(Device)
                        .filter(Device.asset_status == asset_status)
                        .offset((page - 1) * limit)
                        .limit(limit))
                result = await session.execute(stmt)
                data = result.scalars().all()  # 直接获取结果列表
            except SQLAlchemyError as e:
                # 捕获 SQLAlchemy 异常，并返回详细的 HTTP 错误响应
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f'{cls.__name__}-get_device_batch error: {e}'
                )
        return [i for i in data]
