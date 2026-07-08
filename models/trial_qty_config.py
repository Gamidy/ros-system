"""试制数量配置 — 按项目等级(T/A/B/C)预设试制数量"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class TrialQtyConfig(Base):
    """试制数量配置表 — 按项目等级预设试制数量"""

    __tablename__ = "trial_qty_configs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    project_class = Column(
        String(10),
        nullable=False,
        unique=True,
        index=True,
        comment="项目等级: T/A/B/C",
    )
    trial_qty = Column(Integer, nullable=False, comment="试制数量")
    remark = Column(Text, nullable=True, comment="备注说明")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
