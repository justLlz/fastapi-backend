from sqlalchemy import Column, String

from internal.models import ModelMixin


class User(ModelMixin):
    __tablename__ = "user"

    username = Column(String(64))
    account = Column(String(64))
    phone = Column(String(11))

    @classmethod
    def init_by_phone(cls, phone):
        return cls.create(
            phone=phone,
        )
