"""供应商评估管理"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Float
from app.core.database import Base


class SupplierEvaluation(Base):
    """供应商评估记录"""
    __tablename__ = "supplier_evaluations_new"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    supplier_name = Column(String(100), nullable=False, comment="供应商名称")
    eval_period = Column(String(30), default="monthly", comment="评估周期: monthly/quarterly/yearly")
    eval_date = Column(Date, nullable=True, comment="评估日期")
    quality_score = Column(Float, default=0, comment="质量得分 0-100")
    delivery_score = Column(Float, default=0, comment="交付得分 0-100")
    price_score = Column(Float, default=0, comment="价格得分 0-100")
    service_score = Column(Float, default=0, comment="服务得分 0-100")
    total_score = Column(Float, default=0, comment="综合得分")
    grade = Column(String(10), default="B", comment="等级: A/B/C/D")
    comment = Column(Text, nullable=True, comment="评估意见")
    evaluator = Column(String(50), nullable=True, comment="评估人")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
