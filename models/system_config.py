"""系统配置模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.core.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    key = Column(String(64), unique=True, nullable=False, index=True,  # key)
    value = Column(Text, nullable=False,  # value)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,  # updated_at)
