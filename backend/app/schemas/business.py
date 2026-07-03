"""经营分析看板 — Pydantic Schema（参考美的经营分析会体系）"""
from pydantic import BaseModel, Field
from typing import Optional


# ═══════════════ 产销协同（T+3产销） ═══════════════

class ProductionSalesPillar(BaseModel):
    """产销协同维度 — T+3产销"""
    # 项目管道
    total_projects: int = 0
    running_projects: int = 0
    completed_projects: int = 0
    overdue_projects: int = 0
    # 产品策划管道
    total_plans: int = 0
    draft_plans: int = 0
    costing_plans: int = 0
    released_plans: int = 0
    # BOM/物料
    total_boms: int = 0
    total_parts: int = 0
    # 转化率
    plan_to_project_rate: float = 0.0
    # T+3 补充指标
    avg_delivery_cycle_days: Optional[float] = None
    inventory_turnover_rate: Optional[float] = None
    on_time_delivery_rate: Optional[float] = None


# ═══════════════ 财务管控（老虎管控） ═══════════════

class FinancialControlPillar(BaseModel):
    """财务管控维度 — 老虎管控"""
    # 采购
    total_purchase_orders: int = 0
    pending_purchase_orders: int = 0
    total_purchase_amount: float = 0.0
    # 供应商
    total_suppliers: int = 0
    active_suppliers: int = 0
    # 成本核算
    cost_accounting_periods: int = 0
    cost_orders_count: int = 0
    cost_execution_rate: float = 0.0
    cost_overrun_alerts: int = 0
    # 财务指标
    revenue: Optional[float] = None
    gross_profit_rate: Optional[float] = None
    net_profit_rate: Optional[float] = None
    r_and_d_budget: Optional[float] = None
    r_and_d_spent: Optional[float] = None


# ═══════════════ 增长引擎（ToB+海外+新市场） ═══════════════

class GrowthEnginePillar(BaseModel):
    """增长引擎维度 — ToB+海外+新市场"""
    # 市场
    total_markets: int = 0
    r32_markets: int = 0
    r410a_markets: int = 0
    # 竞品
    total_competitors: int = 0
    competitor_markets_count: int = 0
    # 认证
    total_cert_projects: int = 0
    cert_projects_in_progress: int = 0
    # 产品
    total_products: int = 0
    total_versions: int = 0
    # 收入
    overseas_revenue: Optional[float] = None
    tob_revenue: Optional[float] = None
    domestic_revenue: Optional[float] = None
    total_revenue: Optional[float] = None
    market_share: Optional[float] = None


# ═══════════════ 效率指标（AI提效+数字化） ═══════════════

class EfficiencyMetricsPillar(BaseModel):
    """效率指标维度 — AI提效+数字化"""
    # 项目效率
    on_time_rate: float = 0.0
    avg_project_duration_days: float = 0.0
    # 质量效率
    test_pass_rate: float = 0.0
    issue_close_rate: float = 0.0
    # 研发效率
    phase_gate_pass_rate: float = 0.0
    # 系统活跃
    alert_count: int = 0
    overdue_alert_count: int = 0
    # AI数字化
    ai_agent_count: Optional[int] = None
    monthly_cost_savings: Optional[float] = None


# ═══════════════ 经营分析会总响应 ═══════════════

class BusinessAnalysisResponse(BaseModel):
    """经营分析看板 — 四维聚合响应"""
    production_sales: ProductionSalesPillar = Field(default_factory=ProductionSalesPillar)
    financial_control: FinancialControlPillar = Field(default_factory=FinancialControlPillar)
    growth_engine: GrowthEnginePillar = Field(default_factory=GrowthEnginePillar)
    efficiency: EfficiencyMetricsPillar = Field(default_factory=EfficiencyMetricsPillar)
