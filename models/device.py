from sqlalchemy import BigInteger, Column, String

from models import ModelMixin


class Device(ModelMixin):
    __tablename__ = 'device'

    number = Column(String(128), nullable=False, comment='设备编号')
    name = Column(String(32), nullable=False, comment='设备名称')
    gpu_model = Column(String(32), nullable=False, comment='显卡型号')
    supplier = Column(String(32), nullable=False, comment='供应商')
    location = Column(String(16), nullable=False, comment='位置')
    version = Column(String(32), nullable=False, comment='版本')
    cui_version = Column(String(32), nullable=False, comment='cui 版本')
    status = Column(String(8), nullable=False, comment='状态')
    stock_at = Column(BigInteger, nullable=False, comment='入库时间')
    # updated_at = Column(BigInteger, nullable=False, comment='更新时间')
    # created_at = Column(BigInteger, nullable=False, comment='创建时间')