"""ProductPlan 产品策划核心模型

ProductPlan = 策划层（Planning Layer），
Project = 执行层（Execution Layer），
两者通过 APPROVED → 自动生成 Project 连接。

BOMType 枚举定义在此，供下游 BOM 模型引用。
"""
import uuid
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SAEnum, func, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


def uuid4_str() -> str:
    return str(uuid.uuid4())


class ProductPlanStage(str, enum.Enum):
    """产品策划流程阶段"""
    DRAFT = "draft"
    COMPETITOR = "competitor"
    DEFINITION = "definition"
    COSTING = "costing"
    TECH_INPUT = "tech_input"
    PROJECT_INIT = "project_init"
    APPROVED = "approved"
    RELEASED = "released"


class CostType(str, enum.Enum):
    """成本类型"""
    TARGET = "target"
    ACTUAL = "actual"
    ESTIMATE = "estimate"


class BOMType(str, enum.Enum):
    """BOM生命周期阶段（ProductPlan驱动逐步生成）"""
    CONCEPT_BOM = "concept_bom"
    DESIGN_BOM = "design_bom"
    PILOT_BOM = "pilot_bom"
    MASS_BOM = "mass_bom"


class ProductPlan(Base):
    """产品策划主表 — ROS v2 核心中枢"""
    __tablename__ = "product_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, comment="策划名称")
    series = Column(String(100), nullable=True, comment="产品系列")
    market = Column(String(100), nullable=True, comment="目标市场")
    # ---- 已迁移到 ProductPlanInitiation 子表（通过 plan.initiation 访问）----
    # product_type, climate_zone, refrigerant, capacity_range, voltage_freq,
    # series_name, energy_rating, ip_ownership, project_duration, dev_category, project_origin
    target_market_detail = Column(String(100), nullable=True, comment="目标市场(详细)")
    # ---- 现有字段 ----
    competitor_id = Column(Integer, ForeignKey("competitor_models.id"), nullable=True, comment="关联竞品ID")
    cost_target = Column(Text, nullable=True, comment="成本目标JSON: {target: float, currency: str}")
    performance_target = Column(Text, nullable=True, comment="技术指标目标JSON: [{param, target, unit}]")
    status = Column(SAEnum(ProductPlanStage), default=ProductPlanStage.DRAFT, nullable=False, comment="流程阶段")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    # ---- 时间戳 ----
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True, comment="创建者用户名")

    # 关联
    competitor = relationship("CompetitorModel", foreign_keys=[competitor_id])
    costs = relationship("Cost", back_populates="product_plan", cascade="all, delete-orphan")
    # ---- 新增子表关联 ----
    initiation = relationship("ProductPlanInitiation", uselist=False, back_populates="product_plan", cascade="all, delete-orphan")
    market_info = relationship("ProductPlanMarket", uselist=False, back_populates="product_plan", cascade="all, delete-orphan")
    tech_spec = relationship("ProductPlanTechSpec", uselist=False, back_populates="product_plan", cascade="all, delete-orphan")
    team_members = relationship("ProductPlanTeam", back_populates="product_plan", cascade="all, delete-orphan")
    # ---- 多租户 ----
    org = relationship("Organization", foreign_keys=[org_id])
    # ---- 多项目关联 ----
    project_links = relationship("ProductPlanProjectLink", back_populates="product_plan", cascade="all, delete-orphan")


class ProductPlanProjectLink(Base):
    """产品策划 ↔ 项目 多对多关联表（支持快照）"""
    __tablename__ = "product_plan_project_links"

    id = Column(Integer, primary_key=True)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    link_type = Column(String(20), default="primary", comment="链接类型: primary/alternative/aborted/snapshot/reference")
    snapshot_data = Column(Text, nullable=True, comment="策划快照JSON（可选）")
    version_major = Column(Integer, default=1, comment="主版本号")
    version_minor = Column(Integer, default=0, comment="次版本号")
    snapshot_schema_version = Column(Integer, default=1, comment="快照数据schema版本")
    scenario_group_id = Column(String(36), nullable=True, comment="方案分组ID(AB评估用)")
    created_at = Column(DateTime, default=func.now())

    product_plan = relationship("ProductPlan", back_populates="project_links")
    project = relationship("Project", back_populates="product_plan_links")


class Cost(Base):
    """成本记录 — 独立表，归属 ProductPlan"""
    __tablename__ = "costs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, comment="归属策划ID")
    cost_type = Column(SAEnum(CostType), nullable=False, comment="成本类型: target/actual/estimate")
    item_name = Column(String(100), nullable=True, comment="成本项名称")
    target_value = Column(Float, nullable=True, comment="目标值")
    actual_value = Column(Float, nullable=True, comment="实际值")
    currency = Column(String(10), default="CNY", comment="币种")
    remark = Column(String(500), nullable=True, comment="备注")
    created_at = Column(DateTime, server_default=func.now())

    product_plan = relationship("ProductPlan", back_populates="costs")


class ProductRequirement(Base):
    """产品需求录入 — 策划链条的起点（P2需求）"""
    __tablename__ = "product_requirements"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    market = Column(String(100), nullable=False, comment="目标市场")
    customer = Column(String(200), nullable=True, comment="客户名称")
    contact = Column(String(100), nullable=True, comment="联系人")
    product_type = Column(String(100), nullable=False, comment="产品类型")
    capacity_target = Column(String(100), nullable=True, comment="目标冷量")
    price_target = Column(Numeric(12, 2), nullable=True, comment="目标价格")
    energy_standard = Column(String(50), nullable=True, comment="能效标准")
    sales_volume_forecast = Column(Integer, nullable=True, comment="年销量预测")
    notes = Column(Text, nullable=True, comment="补充说明")
    status = Column(String(20), default="pending", comment="pending待处理/accepted已采纳/converted已转化/rejected已拒绝")
    reject_reason = Column(String(500), nullable=True, comment="拒绝原因")
    submitter_name = Column(String(100), nullable=True, comment="提交人姓名")
    submitter_phone = Column(String(20), nullable=True, comment="提交人电话")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ProductPlanReview(Base):
    """P4复盘 — 产品策划完结后的复盘记录（1对1关系）"""
    __tablename__ = "product_plan_reviews"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id", ondelete="CASCADE"), nullable=False, unique=True, comment="关联策划ID")
    review_date = Column(DateTime, default=func.now(), comment="复盘日期")
    actual_cost_total = Column(Numeric(12, 2), nullable=True, comment="实际总成本")
    cost_variance_pct = Column(Float, nullable=True, comment="成本偏差百分比")
    actual_launch_date = Column(DateTime, nullable=True, comment="实际上市日期")
    schedule_variance_days = Column(Integer, nullable=True, comment="进度偏差天数")
    market_feedback = Column(Text, nullable=True, comment="市场反馈")
    lessons_learned = Column(Text, nullable=True, comment="经验教训")
    rating = Column(Integer, nullable=True, comment="评分1-5")
    reviewer_id = Column(String(50), nullable=True, comment="复盘人ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    product_plan = relationship("ProductPlan", backref="review", uselist=False)
