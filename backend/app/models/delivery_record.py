"""交付记录模型"""
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func


class DeliveryRecord(Base):
    """交付记录"""
    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    committed_date = Column(Date, comment="承诺交付日期")
    actual_date = Column(Date, nullable=True, comment="实际交付日期")
    cycle_days = Column(Integer, nullable=True, comment="实际周期天数")
    on_time = Column(Boolean, default=True, comment="是否准时交付")
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project")
