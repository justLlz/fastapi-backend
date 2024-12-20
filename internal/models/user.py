from internal.models.mixin import ModelMixin


class User(ModelMixin):
    account = None
    phone = None

    @classmethod
    def init_by_phone(cls, phone):
        return cls.create(
            phone=phone,
        )
