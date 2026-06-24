"""ProductPlan 产品策划核心模型

ProductPlan = 策划层（Planning Layer），
Project = 执行层（Execution Layer），
两者通过 APPROVED → 自动生成 Project 连接。

BOMType 枚举定义在此，供下游 BOM 模型引用。
"""
import uuid
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SAEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


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
    competitor_id = Column(Integer, ForeignKey("competitor_models.id"), nullable=True, comment="关联竞品ID")
    cost_target = Column(Text, nullable=True, comment="成本目标JSON: {target: float, currency: str}")
    performance_target = Column(Text, nullable=True, comment="技术指标目标JSON: [{param, target, unit}]")
    status = Column(SAEnum(ProductPlanStage), default=ProductPlanStage.DRAFT, nullable=False, comment="流程阶段")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, comment="关联项目ID（APPROVED后赋值）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), nullable=True, comment="创建者用户名")

    # 关联
    competitor = relationship("CompetitorModel", foreign_keys=[competitor_id])
    project = relationship("Project", foreign_keys=[project_id])
    costs = relationship("Cost", back_populates="product_plan", cascade="all, delete-orphan")


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
