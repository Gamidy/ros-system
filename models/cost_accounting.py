"""成本核算系统 — S4 数据模型
7张核心表：核算期间 → 工时费率 → 人工成本 → 分摊规则 → 分摊结果 → 核算单主表 → 核算单明细
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SAEnum,
    UniqueConstraint, Index, func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class PeriodStatus(str, enum.Enum):
    """核算期间状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class SheetStatus(str, enum.Enum):
    """核算单状态"""
    DRAFT = "draft"
    FINALIZED = "finalized"


class CostCategory(str, enum.Enum):
    """成本类别"""
    MATERIAL = "material"
    LABOR = "labor"
    OVERHEAD = "overhead"


class AllocationBase(str, enum.Enum):
    """分摊基准"""
    DIRECT_LABOR = "direct_labor"       # 直接人工成本
    DIRECT_MATERIAL = "direct_material"  # 直接材料成本
    TOTAL_COST = "total_cost"            # 总成本
    QUANTITY = "quantity"                # 产品数量


# ═══════════════════════════════════════════
# 1. 核算期间
# ═══════════════════════════════════════════

class CostAccountingPeriod(Base):
    """核算期间 — 按月/季度组织成本核算"""
    __tablename__ = "cost_accounting_periods"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    period_name = Column(String(50), nullable=False, comment="期间名称，如'2026-Q1'")
    start_date = Column(String(10), nullable=False, comment="开始日期，yyyy-MM-dd")
    end_date = Column(String(10), nullable=False, comment="结束日期，yyyy-MM-dd")
    status = Column(SAEnum(PeriodStatus), default=PeriodStatus.DRAFT, nullable=False, comment="状态")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    # 关联
    sheets = relationship("CostAccountingSheet", back_populates="period", cascade="all, delete-orphan")
    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_ca_period_org", "org_id"),
        Index("idx_ca_period_status", "status"),
    )


# ═══════════════════════════════════════════
# 2. 成本核算单（核心）
# ═══════════════════════════════════════════

class CostAccountingSheet(Base):
    """成本核算单主表 — 一个产品在一个期间的成本全貌"""
    __tablename__ = "cost_accounting_sheets"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    sheet_no = Column(String(50), nullable=False, unique=True, comment="核算单编号: CAS-YYYYMMDD-XXX")
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, comment="关联策划ID")
    period_id = Column(Integer, ForeignKey("cost_accounting_periods.id"), nullable=False, comment="所属期间ID")
    status = Column(SAEnum(SheetStatus), default=SheetStatus.DRAFT, nullable=False, comment="状态")

    # 物料成本（料）
    material_cost_actual = Column(Float, default=0, comment="物料成本实际值")
    material_cost_target = Column(Float, default=0, comment="物料成本目标值")

    # 人工成本（工）
    labor_cost_actual = Column(Float, default=0, comment="人工成本实际值")
    labor_cost_target = Column(Float, default=0, comment="人工成本目标值")

    # 制造费用（费）
    overhead_cost_actual = Column(Float, default=0, comment="制造费用实际值")
    overhead_cost_target = Column(Float, default=0, comment="制造费用目标值")

    # 合计
    total_cost_actual = Column(Float, default=0, comment="总成本实际值=料+工+费")
    total_cost_target = Column(Float, default=0, comment="总成本目标值=料+工+费")
    variance_amount = Column(Float, default=0, comment="差异额=实际-目标")
    variance_pct = Column(Float, default=0, comment="差异率%")

    currency = Column(String(10), default="CNY", comment="币种")
    remark = Column(Text, nullable=True, comment="备注")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_by = Column(String(50), nullable=True, comment="创建者")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    # 关联
    product_plan = relationship("ProductPlan", foreign_keys=[product_plan_id])
    period = relationship("CostAccountingPeriod", foreign_keys=[period_id], back_populates="sheets")
    items = relationship("CostAccountingItem", back_populates="sheet", cascade="all, delete-orphan")
    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_ca_sheet_no", "sheet_no"),
        Index("idx_ca_sheet_plan", "product_plan_id"),
        Index("idx_ca_sheet_period", "period_id"),
        Index("idx_ca_sheet_org", "org_id"),
    )


# ═══════════════════════════════════════════
# 3. 核算单项明细
# ═══════════════════════════════════════════

class CostAccountingItem(Base):
    """核算单项明细 — 核算单的料工费拆解到具体成本项"""
    __tablename__ = "cost_accounting_items"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    sheet_id = Column(Integer, ForeignKey("cost_accounting_sheets.id"), nullable=False, comment="归属核算单ID")
    cost_category = Column(SAEnum(CostCategory), nullable=False, comment="成本类别: material/labor/overhead")
    item_name = Column(String(100), nullable=False, comment="成本项名称")
    target_amount = Column(Float, default=0, comment="目标金额")
    actual_amount = Column(Float, default=0, comment="实际金额")
    variance = Column(Float, default=0, comment="差异=实际-目标")
    variance_pct = Column(Float, default=0, comment="差异率%")
    source_type = Column(String(50), nullable=True, comment="来源类型: bom_item/labor_record/overhead_rule")
    source_id = Column(Integer, nullable=True, comment="来源记录ID")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    remark = Column(String(500), nullable=True, comment="备注")

    # 关联
    sheet = relationship("CostAccountingSheet", foreign_keys=[sheet_id], back_populates="items")
    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_ca_item_sheet", "sheet_id"),
        Index("idx_ca_item_category", "cost_category"),
    )


# ═══════════════════════════════════════════
# 4. 工时费率配置
# ═══════════════════════════════════════════

class LaborRateConfig(Base):
    """工时费率配置 — 各工序标准工时费率"""
    __tablename__ = "labor_rate_configs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    operation_code = Column(String(50), nullable=False, index=True, comment="工序编码")
    operation_name = Column(String(100), nullable=False, comment="工序名称")
    hourly_rate = Column(Float, nullable=False, comment="工时费率(元/小时)")
    unit = Column(String(10), default="hour", comment="单位")
    status = Column(String(10), default="active", comment="状态: active/inactive")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_lr_org", "org_id"),
        Index("idx_lr_code", "operation_code"),
    )


# ═══════════════════════════════════════════
# 5. 产品人工成本
# ═══════════════════════════════════════════

class ProductLaborCost(Base):
    """产品人工成本 — 各产品各工序的工时和对应人工成本"""
    __tablename__ = "product_labor_costs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, comment="关联策划ID")
    period_id = Column(Integer, ForeignKey("cost_accounting_periods.id"), nullable=False, comment="所属期间ID")
    operation_code = Column(String(50), nullable=False, comment="工序编码")
    operation_name = Column(String(100), nullable=False, comment="工序名称")
    labor_hours = Column(Float, nullable=False, comment="工时数")
    hourly_rate = Column(Float, nullable=False, comment="费率快照(元/小时)")
    total_amount = Column(Float, default=0, comment="金额=工时×费率")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_plc_plan", "product_plan_id"),
        Index("idx_plc_period", "period_id"),
        Index("idx_plc_org", "org_id"),
    )


# ═══════════════════════════════════════════
# 6. 间接费分摊规则
# ═══════════════════════════════════════════

class OverheadAllocationRule(Base):
    """间接费分摊规则 — 定义分摊基准和比例"""
    __tablename__ = "overhead_allocation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    rule_name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(Text, nullable=True, comment="规则说明")
    allocation_base = Column(SAEnum(AllocationBase), nullable=False, comment="分摊基准")
    allocation_rate = Column(Float, nullable=False, comment="分摊比例(%)")
    is_active = Column(Integer, default=1, comment="是否启用: 1启用/0禁用")
    priority = Column(Integer, default=0, comment="执行优先级，数字越小越先")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_oar_org", "org_id"),
        Index("idx_oar_active", "is_active"),
    )


# ═══════════════════════════════════════════
# 7. 产品间接费分摊结果
# ═══════════════════════════════════════════

class ProductOverheadCost(Base):
    """产品间接费分摊结果 — 各产品按规则计算的分摊金额"""
    __tablename__ = "product_overhead_costs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, comment="关联策划ID")
    period_id = Column(Integer, ForeignKey("cost_accounting_periods.id"), nullable=False, comment="所属期间ID")
    rule_id = Column(Integer, ForeignKey("overhead_allocation_rules.id"), nullable=False, comment="关联分摊规则ID")
    base_amount = Column(Float, default=0, comment="分摊基数额")
    allocation_rate = Column(Float, default=0, comment="快照分摊率(%)")
    allocation_amount = Column(Float, default=0, comment="分摊金额=基数×率")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    org = relationship("Organization", foreign_keys=[org_id])

    __table_args__ = (
        Index("idx_poc_plan", "product_plan_id"),
        Index("idx_poc_period", "period_id"),
        Index("idx_poc_rule", "rule_id"),
        Index("idx_poc_org", "org_id"),
    )
