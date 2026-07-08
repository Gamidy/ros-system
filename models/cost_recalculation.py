"""冷量联动成本重算 — 数据模型

2张核心表：
  - cost_recalculation_results  → 重算结果主表
  - cost_recalculation_items    → 重算明细（基准/实际对比行）
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey,
    Index, func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class RecalcStatus(str):
    """重算状态"""
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # 无匹配冷量段


class CostRecalculationResult(Base):
    """冷量联动重算结果 — 一次重算的全貌"""

    __tablename__ = "cost_recalculation_results"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, comment="关联策划ID")
    period_id = Column(Integer, ForeignKey("cost_accounting_periods.id"), nullable=True, comment="所属期间ID")
    sheet_id = Column(Integer, ForeignKey("cost_accounting_sheets.id"), nullable=True, comment="关联核算单ID")

    # 冷量信息（快照）
    main_capacity = Column(String(50), nullable=True, comment="产品主销容量")
    matched_btu = Column(Integer, nullable=True, comment="匹配到的BTU值")
    capacity_key = Column(String(20), nullable=True, comment="冷量段标识")

    # 基准成本（按冷量段单价计算）
    baseline_material_cost = Column(Float, default=0, comment="冷量基准物料成本(元)")
    complexity_factor = Column(Float, default=1.0, comment="复杂度系数（保留扩展）")

    # BOM实际成本（快照）
    actual_bom_cost = Column(Float, default=0, comment="实际BOM物料成本(元)")
    bom_id = Column(Integer, nullable=True, comment="关联BOM ID（快照）")
    bom_no = Column(String(50), nullable=True, comment="BOM编号快照")

    # 对比
    variance_amount = Column(Float, default=0, comment="差异=实际-基准(元)")
    variance_pct = Column(Float, default=0, comment="差异率(%)")
    cost_efficiency_score = Column(Float, default=0, comment="成本效率评分 0-100（越高越好）")
    status = Column(String(20), default=RecalcStatus.COMPLETED, comment="状态: completed/failed/skipped")

    # 触发方式
    trigger_source = Column(String(50), default="manual", comment="触发方式: manual/eco_effective/auto")

    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_by = Column(String(50), nullable=True, comment="触发者")
    created_at = Column(DateTime, server_default=func.now(), comment="重算时间")
    remark = Column(Text, nullable=True, comment="备注")

    # 关联
    items = relationship("CostRecalculationItem", back_populates="result", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_crr_plan", "product_plan_id"),
        Index("idx_crr_period", "period_id"),
        Index("idx_crr_sheet", "sheet_id"),
        Index("idx_crr_btu", "matched_btu"),
        Index("idx_crr_created", "created_at"),
    )


class CostRecalculationItem(Base):
    """重算明细 — 每行代表一个对比维度（物料/人工/费用）"""

    __tablename__ = "cost_recalculation_items"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    result_id = Column(Integer, ForeignKey("cost_recalculation_results.id"), nullable=False, comment="归属重算结果ID")
    dimension = Column(String(50), nullable=False, comment="维度: material/labor/overhead")
    item_name = Column(String(100), nullable=False, comment="项目名称")
    baseline_amount = Column(Float, default=0, comment="基准金额(元)")
    actual_amount = Column(Float, default=0, comment="实际金额(元)")
    variance = Column(Float, default=0, comment="差异(元)")
    variance_pct = Column(Float, default=0, comment="差异率(%)")
    remark = Column(String(500), nullable=True, comment="备注")

    result = relationship("CostRecalculationResult", foreign_keys=[result_id], back_populates="items")

    __table_args__ = (
        Index("idx_cri_result", "result_id"),
    )
