"""能力段原型单价 — 按冷量段(BTU)预设单价(万元)"""
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.core.database import Base


class CapacityUnitCost(Base):
    """能力段单价表 — 不同冷量段的原型单价"""

    __tablename__ = "capacity_unit_costs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    capacity_key = Column(
        String(20),
        nullable=False,
        index=True,
        comment="冷量段标识, 如'22K'",
    )
    btu = Column(Integer, nullable=False, comment="BTU值, 如22000")
    unit_cost_w = Column(Float, nullable=False, comment="单价(万元), 如0.178")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
