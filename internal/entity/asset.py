from enum import Enum


class AssetStatus(str, Enum):
    # 已经上线
    ONLINE = "online"
    # 未上线
    OFFLINE = "offline"
