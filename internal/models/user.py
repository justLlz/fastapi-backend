from internal.models import MixinModel


class User(MixinModel):
    account = None
    phone = None

    @classmethod
    def init_by_phone(cls, phone):
        return cls.create(
            phone=phone,
        )


class ManageUser(MixinModel):
    account = None
    password = None
