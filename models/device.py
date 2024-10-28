from sqlalchemy import BigInteger, Column, String, UniqueConstraint

from models import ModelMixin


class Device(ModelMixin):
    __tablename__ = 'device'
    __table_args__ = (
        UniqueConstraint('number', 'name', name='number_name'),
    )

    number = Column(String(128), nullable=False, comment='设备编号')
    name = Column(String(32), nullable=False, comment='设备名称')
    gpu_brand = Column(String(32), nullable=False, comment='品牌型号')
    gpu_model = Column(String(32), nullable=False, comment='显卡型号')
    gpu_number = Column(String(32), nullable=False, comment='显卡编号')
    memory = Column(String(32), nullable=False, comment='内存')
    hard_disk = Column(String(32), nullable=False, comment='硬盘')
    mac_address = Column(String(32), nullable=False, comment='mac地址')
    operate_system = Column(String(32), nullable=False, comment='操作系统')
    ip_address = Column(String(32), nullable=False, comment='ip地址')
    supplier = Column(String(32), nullable=False, comment='供应商')
    location = Column(String(16), nullable=False, comment='放置位置')
    cui_version = Column(String(32), nullable=False, comment='cui 版本')
    other_info = Column(String(128), nullable=False, comment='其他信息')
    status = Column(String(8), nullable=False, comment='状态: 关机-off,使用中-on,闲置中-free')
    asset_status = Column(String(8), nullable=False, comment='资产状态: 已经上线-online, 未上线-offline')
    remarks = Column(String(128), nullable=False, comment='备注')
    stocked_at = Column(BigInteger, nullable=False, comment='入库时间')
