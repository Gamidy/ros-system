"""收入渠道模型"""
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func


class RevenueByChannel(Base):
    """收入渠道"""
    __tablename__ = "revenue_by_channel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), comment="期间 YYYY-MM")
    channel_type = Column(String(20), comment="渠道类型: tob/overseas/domestic_retail")
    amount = Column(Float, comment="收入金额(万元)")
    yoy_growth = Column(Float, nullable=True, comment="同比增长率%")
    created_at = Column(DateTime, server_default=func.now())
