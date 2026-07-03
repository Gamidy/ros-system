"""CostSaving — 降本记录模型

记录各项降本措施带来的成本节约数据，用于成本分析看板。
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from app.core.database import Base


class CostSaving(Base):
    """降本记录 — 跟踪各项降本措施的节约金额与核验状态"""
    __tablename__ = "cost_saving_records"

    id = Column(Integer, primary_key=True)
    source = Column(String(100), comment="降本来源: BOM优化/供应商切换/工艺改进/自动化")
    amount = Column(Float, comment="降本金额(万元)")
    period = Column(String(7), comment="期间 YYYY-MM")
    verified = Column(Boolean, default=False, comment="是否已核验")
    created_at = Column(DateTime, server_default=func.now())
