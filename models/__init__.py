"""数据库模型类"""
from datetime import datetime
from typing import List, Optional, Any, Union, Tuple

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, SmallInteger
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON, BIGINT
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session, relationship, foreign
from sqlalchemy.sql import func, literal, cast


class ModelMixin:
    id = Column(Integer, primary_key=True)
    create_time = Column(DateTime, default=datetime.now)
    create_time._creation_order = 9998
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    update_time._creation_order = 9999

    def save(self, db: Session):
        db.add(self)
        db.commit()
        db.refresh(self)

    def delete(self, db: Session):
        db.delete(self)
        db.commit()

    @classmethod
    def get(cls, db: Session, id: int):
        return db.query(cls).get(id)

    def update(self, update_record: BaseModel):
        update_data = update_record.dict(skip_defaults=True, exclude={})
        cols = self.__class__.__table__.columns.keys()
        for col in cols:
            if col in update_data:
                setattr(self, col, update_data[col])
