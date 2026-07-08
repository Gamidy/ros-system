"""间接成本配置 — 可配置的间接成本金额"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.core.database import Base


class IndirectCostConfig(Base):
    """间接成本配置表 — key-value 形式的间接成本项"""

    __tablename__ = "indirect_cost_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="配置键, 如'default'",
    )
    amount = Column(Float, nullable=False, default=5000, comment="金额(元)")
    description = Column(Text, nullable=True, comment="说明")
    created_at = Column(DateTime, server_default=func.now())
