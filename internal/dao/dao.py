from fastapi import HTTPException
from loguru import logger
from starlette import status

from internal.entity.asset import EventCategory
from internal.models.asset import AssetOperationLog
from internal.infra.db import get_local_session


async def update_and_insert_log(update_stmt: str, user_id: int, biz_id: int, event: EventCategory, change_dict: dict):
    operation_log = AssetOperationLog.create_operate_log(user_id, biz_id, event, change_dict)
    async with get_local_session() as session:
        try:
            async with session.begin():
                await session.execute(update_stmt)
                session.add(operation_log)
        except Exception as e:
            logger.error(repr(e))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
