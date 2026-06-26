"""项目管理 — Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ═══════════════ 项目群 ═══════════════

class ProgramCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProgramOut(ProgramCreate):
    id: int
    status: str
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 项目 ═══════════════

class ProjectCreate(BaseModel):
    code: Optional[str] = None
    name: str = Field(max_length=200)
    program_id: Optional[int] = None
    product_code: Optional[str] = None
    project_class: Optional[str] = Field(default='C', pattern="^(T|A|B|C)$")
    source: Optional[str] = None
    source_category: Optional[str] = None
    dev_modules: Optional[str] = None
    change_impacts: Optional[str] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    critical_path: Optional[str] = None
    market_policy: Optional[str] = None
    annual_planning_ref: Optional[str] = None
    budget: Optional[int] = None
    # Sheet 1 - 项目概述
    product_type: Optional[str] = None
    target_market: Optional[str] = None
    climate_zone: Optional[str] = None
    refrigerant: Optional[str] = None
    capacity_range: Optional[str] = None
    voltage_freq: Optional[str] = None
    series_name: Optional[str] = None
    energy_rating: Optional[str] = None
    ip_ownership: Optional[str] = None
    project_duration: Optional[str] = None
    dev_category: Optional[str] = None
    project_origin: Optional[str] = None
    background_basis: Optional[str] = None
    overall_goal: Optional[str] = None
    tech_goal: Optional[str] = None
    cost_goal: Optional[str] = None
    sales_goal: Optional[str] = None
    cert_goal: Optional[str] = None
    schedule_goal: Optional[str] = None
    patent_goal: Optional[str] = None
    other_goals: Optional[str] = None
    deliverables: Optional[str] = None
    sample_qty: Optional[int] = None
    required_date: Optional[date] = None
    # Sheet 2 - 市场与客户需求
    main_capacity: Optional[str] = None
    energy_efficiency_req: Optional[str] = None
    cert_requirements: Optional[str] = None
    target_price: Optional[str] = None
    customer_requirements: Optional[str] = None
    # Sheet 3 - 技术要求
    core_performance: Optional[str] = None
    safety_compliance: Optional[str] = None
    optional_config: Optional[str] = None
    # Sheet 4 - 成本核算
    dev_cost_items: Optional[str] = None
    economic_indicators: Optional[str] = None
    mold_costs: Optional[str] = None
    prototype_costs_detail: Optional[str] = None
    # Sheet 5 - 团队与职责
    team_members: Optional[str] = None
    # Draft 机制
    is_draft: Optional[bool] = True


class ProjectDraftSave(ProjectCreate):
    """草稿保存专用 Schema — 字段与 ProjectCreate 完全相同，语义区分"""
    pass


class ProjectUpdate(BaseModel):
    """项目更新 - PATCH 请求体"""
    name: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    target_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    description: Optional[str] = None
    customer_name: Optional[str] = None
    other_requirements: Optional[str] = None
    budget: Optional[int] = None


class ProjectOut(ProjectCreate):
    id: int
    status: str
    gates: list["ProjectGateOut"] = []
    risks: list["RiskOut"] = []
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 项目节点 ═══════════════

class ProjectGateCreate(BaseModel):
    gate_code: str
    gate_name: str
    seq: int
    decision_level: Optional[str] = None
    pass_conditions: Optional[str] = None
    is_high_risk_zone: bool = False
    is_hidden: bool = False


class ProjectGateOut(ProjectGateCreate):
    id: int
    project_id: int
    status: str
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    decision: Optional[str] = None
    reviewer: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class GateStatusUpdate(BaseModel):
    status: str
    actual_date: Optional[date] = None
    decision: Optional[str] = None


# ═══════════════ 里程碑/任务/风险 ═══════════════

class MilestoneCreate(BaseModel):
    name: str
    planned_date: Optional[date] = None
    conditions: Optional[str] = None
    gate_code: Optional[str] = None


class MilestoneOut(MilestoneCreate):
    id: int
    project_id: int
    status: str
    actual_date: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


class TaskCreate(BaseModel):
    title: str
    assignee: Optional[str] = None
    milestone_id: Optional[int] = None
    priority: str = "medium"
    planned_date: Optional[date] = None
    due_date: Optional[date] = None
    description: Optional[str] = None


class TaskOut(TaskCreate):
    id: int
    project_id: int
    status: str
    actual_date: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


class RiskCreate(BaseModel):
    title: str
    risk_level: str = "B"
    risk_source: Optional[str] = None
    probability: str = "medium"
    impact: str = "medium"
    mitigation: Optional[str] = None


class RiskOut(RiskCreate):
    id: int
    project_id: int
    status: str
    raised_by: Optional[str] = None
    resolved_at: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


class IssueUpdate(BaseModel):
    root_cause: str | None = None
    solution: str | None = None
    status: str | None = None
