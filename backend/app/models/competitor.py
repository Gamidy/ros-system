"""竞品参数库模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func
from app.core.database import Base


class CompetitorModel(Base):
    """竞品机型参数表"""
    __tablename__ = "competitor_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(80), nullable=False, index=True, comment="品牌")
    model = Column(String(120), nullable=False, index=True, comment="型号")
    market = Column(String(80), nullable=False, index=True, comment="目标市场")
    product_type = Column(String(60), nullable=True, comment="产品类型")
    cooling_capacity = Column(String(40), nullable=True, comment="冷量段")
    cooling_capacity_w = Column(Integer, nullable=True, comment="制冷量(W)")
    heating_capacity_w = Column(Integer, nullable=True, comment="制热量(W)")
    energy_rating = Column(String(40), nullable=True, comment="能效等级")
    cooling_w = Column(Integer, nullable=True, comment="制冷功率(W)")
    heating_w = Column(Integer, nullable=True, comment="制热功率(W)")
    eer = Column(Float, nullable=True, comment="能效比 EER")
    cspf = Column(Float, nullable=True, comment="CSPF能效(越南/印尼)")
    noise_indoor_db = Column(Float, nullable=True, comment="室内噪音(dB)")
    noise_outdoor_db = Column(Float, nullable=True, comment="室外噪音(dB)")
    airflow_m3h = Column(Float, nullable=True, comment="循环风量(m³/h)")
    indoor_size_mm = Column(String(60), nullable=True, comment="内机尺寸(mm)")
    outdoor_size_mm = Column(String(60), nullable=True, comment="外机尺寸(mm)")
    factory_price = Column(String(60), nullable=True, comment="出厂价")
    launch_year = Column(Integer, nullable=True, comment="上市年份")
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
