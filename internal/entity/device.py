from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from internal.entity.asset import AssetStatus
from models.device import Device as DeviceModel, Device


class DeviceStatus(str, Enum):
    # 关机
    OFF = 'off'
    # 使用中
    ON = 'on'
    # 闲置中
    FREE = 'free'


class DeviceBase(BaseModel):
    """基础字段，用于创建、更新、和返回校验的公共字段"""
    number: str = Field(..., max_length=128, description="设备编号")
    name: str = Field(..., max_length=32, description="设备名称")
    gpu_brand: str = Field(..., max_length=32, description="品牌型号")
    gpu_model: str = Field(..., max_length=32, description="显卡型号")
    gpu_number: str = Field(..., max_length=32, description="显卡编号")
    memory: str = Field(..., max_length=32, description="内存")
    hard_disk: str = Field(..., max_length=32, description="硬盘")
    mac_address: str = Field(..., max_length=32, description="mac地址")
    operate_system: str = Field(..., max_length=32, description="操作系统")
    ip_address: str = Field(..., max_length=32, description="ip地址")
    supplier: str = Field(..., max_length=32, description="供应商")
    location: str = Field(..., max_length=16, description="放置位置")
    cui_version: str = Field(..., max_length=32, description="cui 版本")
    other_info: str = Field(..., max_length=128, description="其他信息")
    status: DeviceStatus = Field(..., max_length=8, description="状态: 关机-off,使用中-on,闲置中-free")
    asset_status: AssetStatus = Field(..., max_length=8, description="资产状态: 已经上线-online, 未上线-offline")
    remarks: str = Field(..., max_length=128, description="备注")
    stocked_at: int = Field(..., description="入库时间，Unix时间戳")

    class Config:
        from_attributes = True


class DeviceCreate(DeviceBase):
    """用于新增设备数据的校验模型"""
    pass


class DeviceUpdate(BaseModel):
    """用于更新设备数据的校验模型，所有字段可选"""
    number: Optional[str] = Field(None, max_length=128, description="设备编号")
    name: Optional[str] = Field(None, max_length=32, description="设备名称")
    gpu_brand: Optional[str] = Field(None, max_length=32, description="品牌型号")
    gpu_model: Optional[str] = Field(None, max_length=32, description="显卡型号")
    gpu_number: Optional[str] = Field(None, max_length=32, description="显卡编号")
    memory: Optional[str] = Field(None, max_length=32, description="内存")
    hard_disk: Optional[str] = Field(None, max_length=32, description="硬盘")
    mac_address: Optional[str] = Field(None, max_length=32, description="mac地址")
    operate_system: Optional[str] = Field(None, max_length=32, description="操作系统")
    ip_address: Optional[str] = Field(None, max_length=32, description="ip地址")
    supplier: Optional[str] = Field(None, max_length=32, description="供应商")
    location: Optional[str] = Field(None, max_length=16, description="放置位置")
    cui_version: Optional[str] = Field(None, max_length=32, description="cui 版本")
    other_info: Optional[str] = Field(None, max_length=128, description="其他信息")
    status: Optional[DeviceStatus] = Field(None, max_length=8, description="状态: 关机-off,使用中-on,闲置中-free")
    asset_status: Optional[AssetStatus] = Field(None, max_length=8, description="资产状态: 已经上线-online, 未上线-offline")
    remarks: Optional[str] = Field(None, max_length=128, description="备注")
    stocked_at: Optional[int] = Field(None, description="入库时间，Unix时间戳")


class DeviceResponse(DeviceBase):
    """用于返回设备数据的校验模型"""
    id: int = Field(..., description="设备主键ID")
    created_at: Optional[int] = Field(None, description="创建时间，Unix时间戳")
    updated_at: Optional[int] = Field(None, description="更新时间，Unix时间戳")


class DeviceEntity:
    @classmethod
    def model_to_dict(cls, m: DeviceModel) -> dict:
        data = DeviceCreate.model_validate(m).model_dump()
        data['id'] = m.id
        return data

    @classmethod
    def batch_model_to_dict(cls, ms: List[Device]) -> List[dict]:
        return [cls.model_to_dict(m) for m in ms]
