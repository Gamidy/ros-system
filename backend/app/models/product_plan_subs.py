"""ProductPlan 子表模型 — Sheet1-5 立项数据

承接从 Project 迁移的立项申报数据：
- ProductPlanInitiation (1:1) 项目概述 Sheet1
- ProductPlanMarket (1:1) 市场与客户需求 Sheet2
- ProductPlanTechSpec (1:1) 技术要求 Sheet3
- ProductPlanTeam (1:N) 团队成员 Sheet5
Sheet4 成本复用已有 Cost 模型+新增 cost_category
"""
from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProductPlanInitiation(Base):
    """项目概述（Sheet1）— 每个 ProductPlan 一条"""
    __tablename__ = "product_plan_initiations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, unique=True, comment="关联策划ID")
    # 产品定义
    product_type = Column(String(50), nullable=True, comment="产品类型")
    target_market = Column(String(100), nullable=True, comment="目标市场")
    climate_zone = Column(String(50), nullable=True, comment="温带")
    refrigerant = Column(String(50), nullable=True, comment="制冷剂")
    capacity_range = Column(String(100), nullable=True, comment="覆盖容量")
    voltage_freq = Column(String(50), nullable=True, comment="电压频率")
    series_name = Column(String(50), nullable=True, comment="系列名称（如 J/K/L/M）")
    energy_rating = Column(String(20), nullable=True, comment="能效等级")
    ip_ownership = Column(String(100), nullable=True, comment="知识产权归属")
    project_duration = Column(String(50), nullable=True, comment="项目周期")
    dev_category = Column(String(50), nullable=True, comment="开发类别")
    project_origin = Column(String(100), nullable=True, comment="项目来源")
    # 背景与目标
    background_basis = Column(Text, nullable=True, comment="项目背景与立项依据")
    overall_goal = Column(Text, nullable=True, comment="总体目标")
    tech_goal = Column(Text, nullable=True, comment="技术目标")
    cost_goal = Column(Text, nullable=True, comment="成本目标")
    sales_goal = Column(Text, nullable=True, comment="销售目标1-3年预测")
    cert_goal = Column(Text, nullable=True, comment="认证目标")
    schedule_goal = Column(Text, nullable=True, comment="进度目标")
    patent_goal = Column(Text, nullable=True, comment="专利目标")
    other_goals = Column(Text, nullable=True, comment="其他目标")
    deliverables = Column(Text, nullable=True, comment="交付物清单")
    sample_qty = Column(Integer, nullable=True, comment="客户样机数量")
    required_date = Column(Date, nullable=True, comment="需求时间")
    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    product_plan = relationship("ProductPlan", foreign_keys=[product_plan_id])


class ProductPlanMarket(Base):
    """市场与客户需求（Sheet2）— 每个 ProductPlan 一条"""
    __tablename__ = "product_plan_markets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, unique=True, comment="关联策划ID")
    main_capacity = Column(String(50), nullable=True, comment="主销容量")
    energy_efficiency_req = Column(String(100), nullable=True, comment="能效要求")
    cert_requirements = Column(Text, nullable=True, comment="认证要求")
    target_price = Column(String(50), nullable=True, comment="目标售价USD")
    customer_requirements = Column(Text, nullable=True, comment="客户关键需求")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    product_plan = relationship("ProductPlan", foreign_keys=[product_plan_id])


class ProductPlanTechSpec(Base):
    """技术要求（Sheet3）— 每个 ProductPlan 一条"""
    __tablename__ = "product_plan_tech_specs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, unique=True, comment="关联策划ID")
    core_performance = Column(Text, nullable=True, comment="核心性能参数JSON")
    safety_compliance = Column(Text, nullable=True, comment="安全合规要求JSON")
    optional_config = Column(Text, nullable=True, comment="选配要求")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    product_plan = relationship("ProductPlan", foreign_keys=[product_plan_id])


class ProductPlanTeam(Base):
    """团队与职责（Sheet5）— 每个 ProductPlan 多条"""
    __tablename__ = "product_plan_teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_plan_id = Column(String(36), ForeignKey("product_plans.id"), nullable=False, comment="关联策划ID")
    role_name = Column(String(50), nullable=False, comment="角色名称")
    member_name = Column(String(50), nullable=True, comment="成员姓名")
    department = Column(String(50), nullable=True, comment="部门")
    responsibility = Column(String(200), nullable=True, comment="职责说明")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    product_plan = relationship("ProductPlan", foreign_keys=[product_plan_id])
