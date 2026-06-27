"""驾驶舱仪表盘 — Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ═══════════════ 概览统计 ═══════════════

class DashboardSummary(BaseModel):
    total_products: int = 0
    active_projects: int = 0
    high_risk_projects: int = 0
    pending_tests: int = 0
    active_certifications: int = 0
    open_quality_issues: int = 0
    unresolved_alerts: int = 0
    cdf_expiring_soon: int = 0
    m4_m6_at_risk: int = 0


# ═══════════════ 多层聚合 ═══════════════

class Layer1SystemHealth(BaseModel):
    """L1 系统健康概览"""
    total_platforms: int = 0
    total_products: int = 0
    total_versions: int = 0
    active_projects: int = 0
    product_status_distribution: dict[str, int] = Field(default_factory=dict)


class RecentProjectSummary(BaseModel):
    """L2 近期项目摘要"""
    id: int
    code: Optional[str] = None
    name: str
    status: str
    project_class: Optional[str] = None
    target_end_date: Optional[date] = None
    owner: Optional[str] = None

    class Config:
        from_attributes = True


class Layer2ProjectOps(BaseModel):
    """L2 项目运营概览"""
    project_count: int = 0
    on_time_rate: float = 0.0
    overdue_count: int = 0
    pending_approvals_count: int = 0
    recent_projects: list[RecentProjectSummary] = Field(default_factory=list)
    project_status_distribution: dict[str, int] = Field(default_factory=dict)


class Layer4ACMetrics(BaseModel):
    """L4 进度-测试-品质-成本综合指标"""
    phase_progress: Optional[dict[str, float]] = Field(default_factory=dict)
    test_pass_rate: float = 0.0
    issue_close_rate: float = 0.0
    cost_execution_rate: float = 0.0
    generalization_rate: float = 0.0
    phase_progress_array: list[dict] = Field(default_factory=list)
    total_issues: int = 0
    closed_issues: int = 0


class KpiDetailItem(BaseModel):
    """KPI卡片明细数据项"""
    id: str | int
    name: str
    market: Optional[str] = None
    status: str
    series: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    code: Optional[str] = None
    target_end_date: Optional[str] = None
    type: str = "plan"  # plan / project / approval


class DashboardResponse(BaseModel):
    """驾驶舱多层聚合响应"""
    layer1_system_health: Layer1SystemHealth = Field(default_factory=Layer1SystemHealth)
    layer2_project_ops: Layer2ProjectOps = Field(default_factory=Layer2ProjectOps)
    layer3_penetration: Optional[dict] = None
    layer4_ac_metrics: Layer4ACMetrics = Field(default_factory=Layer4ACMetrics)
    # D3-4: 角色化视图
    role_view: str = "management"  # management | pm | rd | quality
    pm_competitor_summary: Optional[dict] = None  # PM: 竞品动态摘要
    rd_bom_summary: Optional[dict] = None          # RD: BOM状态摘要
    quality_cert_summary: Optional[dict] = None     # Quality: 认证进度摘要


# ═══════════════ D3-3: 预警摘要 ═══════════════

class AlertItem(BaseModel):
    """预警条目"""
    type: str  # overdue | stuck | cost_overrun
    plan_id: str
    plan_name: str
    message: str
    severity: int  # 3=overdue, 2=cost_overrun, 1=stuck
    status: Optional[str] = None
    created_at: Optional[datetime] = None


class AlertsSummaryResponse(BaseModel):
    """预警摘要响应"""
    overdue_count: int = 0
    stuck_count: int = 0
    cost_overrun_count: int = 0
    alerts: list[AlertItem] = Field(default_factory=list)
