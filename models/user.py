from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship

from models import ModelMixin
from utils.database import Base


class Role(Base, ModelMixin):
    name = Column(String(128))


class User(Base, ModelMixin):
    """
    User Table
    """
    username = Column(String(128), unique=True, nullable=True)
    email = Column(String(256), unique=True, nullable=True)
    enterprise_id = Column(Integer, index=True)
    role_id = Column(Integer, index=True)
    is_removed = Column(Boolean, default=False)

    role = relationship('Role', uselist=False, viewonly=True, lazy='joined', primaryjoin=role_id == foreign(Role.id))
