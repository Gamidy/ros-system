"""PM 配置表 — 配件默认 & 功能默认"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class AccessoryDefault(Base):
    """配件默认配置表"""
    __tablename__ = "accessory_defaults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(50), nullable=False, index=True, comment="目标市场")
    name = Column(String(100), nullable=False, comment="配件名称")
    default_selection = Column(String(20), default="选配", comment="默认选配: 标配/选配/不配")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class FeatureDefault(Base):
    """功能默认配置表"""
    __tablename__ = "feature_defaults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(50), nullable=False, index=True, comment="目标市场")
    name = Column(String(100), nullable=False, comment="功能名称")
    default_selection = Column(String(20), default="选配", comment="默认选配: 标配/选配/不配")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
