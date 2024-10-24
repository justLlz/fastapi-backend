from pydantic import BaseModel, Field
from typing import Optional

from utils import int_utc_timestamp


class DeviceCreate(BaseModel):
    number: str = Field(..., max_length=128, description="设备编号")
    name: str = Field(..., max_length=32, description="设备名称")
    gpu_model: str = Field(..., max_length=32, description="显卡型号")
    supplier: str = Field(..., max_length=32, description="供应商")
    location: str = Field(..., max_length=16, description="位置")
    version: str = Field(..., max_length=32, description="版本")
    cui_version: str = Field(..., max_length=32, description="CUI 版本")
    status: str = Field(..., max_length=8, description="状态")
    stock_at: int = Field(..., description="入库时间，Unix 时间戳")
    updated_at: int = Field(default=int_utc_timestamp(), description="更新时间，Unix 时间戳")
    created_at: int = Field(default=int_utc_timestamp(), description="创建时间，Unix 时间戳")

    class Config:
        from_attributes = True

    def to_dict(self, ):
        data = self.model_dump(exclude_unset=True)
        return data


class DeviceUpdate(BaseModel):
    number: Optional[str] = Field(None, max_length=128, description="设备编号")
    name: Optional[str] = Field(None, max_length=32, description="设备名称")
    gpu_model: Optional[str] = Field(None, max_length=32, description="显卡型号")
    supplier: Optional[str] = Field(None, max_length=32, description="供应商")
    location: Optional[str] = Field(None, max_length=16, description="位置")
    version: Optional[str] = Field(None, max_length=32, description="版本")
    cui_version: Optional[str] = Field(None, max_length=32, description="CUI 版本")
    status: Optional[str] = Field(None, max_length=8, description="状态")
    stock_at: Optional[int] = Field(None, description="入库时间，Unix 时间戳")
    updated_at: Optional[int] = Field(None, description="更新时间，Unix 时间戳")

    class Config:
        from_attributes = True
