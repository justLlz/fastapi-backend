from models.device import Device as DeviceModel
from schemas.device import DeviceCreate


class DeviceEntity:

    @classmethod
    def model_to_dict(cls, m: DeviceModel) -> dict:
        data = DeviceCreate.model_validate(m).model_dump(exclude_unset=True)
        return data
