"""项目管理模型: Program → Project(T/A/B/C) → M1~M9 Gate → Task + 风险 + 里程碑"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Program(Base):
    """项目群 — 上层容器"""
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="项目群编号")
    name = Column(String(200), nullable=False, comment="项目群名称，如'2027海外新品计划'")
    description = Column(Text, nullable=True)
    status = Column(String(20), default="active", comment="active/completed/cancelled")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    projects = relationship("Project", back_populates="program")


class Project(Base):
    """项目 — 基本管理单元"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="项目编号")
    name = Column(String(200), nullable=False, comment="项目名称")
    # 归属
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True, comment="归属Program")
    product_code = Column(String(50), nullable=True, comment="关联产品编码")
    # L1: 项目等级 T/A/B/C
    project_class = Column(String(10), nullable=False, comment="T级/A级/B级/C级")
    # L2: 项目场景
    source = Column(String(50), nullable=True, comment="来源: 年度规划/客户需求/品质整改/研发降本/供应链二供/工艺提效/法规升级")
    source_category = Column(String(30), nullable=True, comment="归类: product_creation/product_optimization")
    # L3: 开发模块 (JSON数组: ["结构","系统","电控"])
    dev_modules = Column(String(200), nullable=True, comment="开发模块JSON")
    # L4: 变更影响 (JSON数组: ["性能","安全","认证","市场"])
    change_impacts = Column(String(200), nullable=True, comment="变更影响JSON")
    # 生命周期
    status = Column(String(20), default="planning", comment="planning/running/completed/paused/cancelled")
    start_date = Column(Date, nullable=True)
    target_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    # 关键路径
    critical_path = Column(String(200), nullable=True, comment="T项目关键路径: 结构优先")
    # 管理信息
    owner = Column(String(50), nullable=True, comment="项目经理")
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="项目负责人(用户ID)")
    description = Column(Text, nullable=True)
    # 产品经理业务字段
    market_policy = Column(String(200), nullable=True, comment="市场政策背景")
    annual_planning_ref = Column(String(100), nullable=True, comment="年度规划关联")
    budget = Column(Integer, nullable=True, comment="项目预算(元)")
    # ══════════════════════════════════════════
    # Sheet 1 - 项目概述 (Product Initiation)
    # ══════════════════════════════════════════
    product_type = Column(String(50), nullable=True, comment="产品类型")
    target_market = Column(String(100), nullable=True, comment="目标市场")
    climate_zone = Column(String(50), nullable=True, comment="温带")
    refrigerant = Column(String(50), nullable=True, comment="制冷剂")
    capacity_range = Column(String(100), nullable=True, comment="覆盖容量")
    voltage_freq = Column(String(50), nullable=True, comment="电压频率")
    series_name = Column(String(50), nullable=True, comment="系列名称（如 J/K/L/M）")
    energy_rating = Column(String(20), nullable=True, comment="能效等级（如 5星/3星/1星）")
    ip_ownership = Column(String(100), nullable=True, comment="知识产权归属")
    project_duration = Column(String(50), nullable=True, comment="项目周期")
    dev_category = Column(String(50), nullable=True, comment="开发类别")
    project_origin = Column(String(100), nullable=True, comment="项目来源")
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
    # ══════════════════════════════════════════
    # Sheet 2 - 市场与客户需求
    # ══════════════════════════════════════════
    main_capacity = Column(String(50), nullable=True, comment="主销容量")
    energy_efficiency_req = Column(String(100), nullable=True, comment="能效要求")
    cert_requirements = Column(Text, nullable=True, comment="认证要求")
    target_price = Column(String(50), nullable=True, comment="目标售价USD")
    customer_requirements = Column(Text, nullable=True, comment="客户关键需求")
    # ══════════════════════════════════════════
    # Sheet 3 - 技术要求
    # ══════════════════════════════════════════
    core_performance = Column(Text, nullable=True, comment="核心性能参数JSON")
    safety_compliance = Column(Text, nullable=True, comment="安全合规要求JSON")
    optional_config = Column(Text, nullable=True, comment="选配要求")
    # ══════════════════════════════════════════
    # Sheet 4 - 成本核算
    # ══════════════════════════════════════════
    dev_cost_items = Column(Text, nullable=True, comment="开发费用明细JSON")
    economic_indicators = Column(Text, nullable=True, comment="经济指标JSON")
    mold_costs = Column(Text, nullable=True, comment="模具费用JSON")
    prototype_costs_detail = Column(Text, nullable=True, comment="样机费用JSON")
    test_costs = Column(Text, nullable=True, comment="测试费用JSON")
    cert_costs = Column(Text, nullable=True, comment="认证费用JSON（自动生成）")
    labor_costs = Column(Text, nullable=True, comment="人工费用JSON")
    # ══════════════════════════════════════════
    # Sheet 5 - 团队与职责
    # ══════════════════════════════════════════
    team_members = Column(Text, nullable=True, comment="团队成员JSON")
    # ══════════════════════════════════════════
    # Draft 机制
    # ══════════════════════════════════════════
    is_draft = Column(Boolean, default=True, nullable=False, comment="是否草稿")
    customer_name = Column(String(100), nullable=True, comment="customer_name")
    other_requirements = Column(Text, nullable=True, comment="other_requirements")
    accessory_config = Column(Text, nullable=True, comment="accessory_config")
    feature_config = Column(Text, nullable=True, comment="feature_config")
    fob_price = Column(String(50), nullable=True, comment="fob_price")
    bom_cost_target = Column(String(50), nullable=True, comment="bom_cost_target")
    bom_cost_ratio = Column(String(50), nullable=True, comment="bom_cost_ratio")
    manufacturing_cost = Column(String(50), nullable=True, comment="manufacturing_cost")
    gross_margin = Column(String(50), nullable=True, comment="gross_margin")
    annual_sales_forecast = Column(String(50), nullable=True, comment="annual_sales_forecast")
    product_lifecycle = Column(String(50), nullable=True, comment="product_lifecycle")
    mold_inner = Column(Text, nullable=True, comment="mold_inner")
    mold_outer = Column(Text, nullable=True, comment="mold_outer")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    program = relationship("Program", back_populates="projects")
    gates = relationship("ProjectGate", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")


class ProjectGate(Base):
    """M1-M9 Gate 节点"""
    __tablename__ = "project_gates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    gate_code = Column(String(10), nullable=False, comment="M1~M9")
    gate_name = Column(String(100), nullable=False, comment="Gate名称")
    seq = Column(Integer, nullable=False, comment="排序 1-9")
    # 决策层
    decision_level = Column(String(20), nullable=True, comment="总经理/项目经理 决策层")
    decider = Column(String(50), nullable=True, comment="决策人")
    # 状态
    status = Column(String(20), default="pending", comment="pending/passed/failed/skipped")
    planned_date = Column(Date, nullable=True)
    actual_date = Column(Date, nullable=True)
    # 点亮条件 (JSON: 客观达成条件列表)
    pass_conditions = Column(Text, nullable=True, comment="点亮条件JSON")
    # 决策记录
    decision = Column(Text, nullable=True, comment="决策记录")
    reviewer = Column(String(50), nullable=True)
    # 特殊标记
    is_high_risk_zone = Column(Boolean, default=False, comment="M4-M6高风险区标记")
    is_hidden = Column(Boolean, default=False, comment="M5A隐藏节点")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="gates")


class Milestone(Base):
    """里程碑节点 — 与Task自动联动"""
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    planned_date = Column(Date, nullable=True)
    actual_date = Column(Date, nullable=True)
    status = Column(String(20), default="pending", comment="pending/achieved/delayed")
    # 点亮条件
    conditions = Column(Text, nullable=True, comment="点亮条件JSON")
    # 关联Gate
    gate_code = Column(String(10), nullable=True, comment="关联M1~M9")
    # 依赖链: 里程碑延期传导
    depends_on_milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True, comment="依赖的上游里程碑")
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="milestones")
    depends_on = relationship("Milestone", remote_side=[id], backref="downstream_milestones")


class Task(Base):
    """项目任务"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True, comment="关联里程碑")
    title = Column(String(200), nullable=False)
    assignee = Column(String(50), nullable=True)
    status = Column(String(20), default="todo", comment="todo/in_progress/done/blocked")
    priority = Column(String(10), default="medium", comment="low/medium/high/urgent")
    planned_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    actual_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    milestone = relationship("Milestone")


class Risk(Base):
    """项目风险追踪"""
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    risk_level = Column(String(10), default="B", comment="A级(阻塞)/B级(影响)/C级(轻微)")
    risk_source = Column(String(50), nullable=True, comment="来源: 模具/物料/认证/人员/外部")
    probability = Column(String(10), default="medium", comment="low/medium/high")
    impact = Column(String(10), default="medium", comment="low/medium/high")
    mitigation = Column(Text, nullable=True, comment="缓解措施")
    status = Column(String(20), default="open", comment="open/monitoring/resolved")
    raised_by = Column(String(50), nullable=True)
    resolved_at = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="risks")
