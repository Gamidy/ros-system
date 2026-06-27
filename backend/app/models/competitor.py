"""竞品参数库模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func, text
from app.core.database import Base

# 数据来源枚举
COMPETITOR_SOURCE_MANUAL = "manual"
COMPETITOR_SOURCE_AUTO = "auto"
COMPETITOR_SOURCES = [COMPETITOR_SOURCE_MANUAL, COMPETITOR_SOURCE_AUTO]
"""竞品数据来源: manual=人工录入, auto=自动采集"""


class CompetitorModel(Base):
    """竞品档案"""
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
    source = Column(String(32), nullable=False, default="manual",
                    server_default=text("'manual'"),
                    comment="数据来源: manual=人工录入, auto=自动采集")
    source_url = Column(String(1024), nullable=True, comment="来源 URL（自动采集时的产品页面链接）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
