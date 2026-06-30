"""ProductPlan Schemas — 所有Pydantic Schemas + 辅助函数

从 product_plan.py 提取的纯 Schema/辅助函数层，不含 @router 装饰器或 API 端点。

被引用于:
- product_plan.py (API 端点)
- product_plan_review.py (P4复盘)
- 前端/测试等
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

# ── 子表 Schema 引用 ──
from app.api.product_plan_subs import (
    InitiationOut as _InitiationOut,
    MarketOut as _MarketOut,
    TechSpecOut as _TechSpecOut,
    TeamOut as _TeamOut,
)
from app.core.constants import VALID_PRODUCT_TYPES
from app.schemas.product_plan_link import ProductPlanLinkOut
from app.services.product_plan_workflow import STAGE_LABELS

# ── Models（仅类型引用，供辅助函数使用）──
from app.models.product_plan import Cost, ProductPlan, ProductPlanStage


# ═══════════════════════════════════════
# 输入 Schemas（Request Body）
# ═══════════════════════════════════════

class CostCreate(BaseModel):
    """创建成本记录"""
    cost_type: str = "target"
    item_name: Optional[str] = None
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    currency: str = "CNY"
    remark: Optional[str] = None


class PlanCreate(BaseModel):
    """创建策划"""
    name: str = Field(..., min_length=1, max_length=200)
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None
    # [P0-2] 创建策划字段对齐
    product_type: str = Field(..., min_length=1, max_length=100, description="产品类型（必填）")
    market_id: str = Field(..., min_length=1, max_length=36, description="目标市场ID（必填）")

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        if v not in VALID_PRODUCT_TYPES:
            raise ValueError(f"不支持的产品类型: {v}")
        return v


class AdvancePlanRequest(BaseModel):
    """推进流程请求体 — 审批意见"""
    comment: Optional[str] = None


class SetStageRequest(BaseModel):
    """直接设置阶段请求体"""
    stage: str = Field(..., description="目标阶段值")


class PlanValidateRequest(BaseModel):
    """策划校验请求体 — 提交待校验的策划数据"""
    name: Optional[str] = None
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None
    target_cost: Optional[float] = None
    cooling_capacity_w: Optional[float] = None
    heating_capacity_w: Optional[float] = None
    eer: Optional[float] = None
    noise_indoor_db: Optional[float] = None


class PlanUpdate(BaseModel):
    """更新策划基本信息"""
    name: Optional[str] = None
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None


# ═══════════════════════════════════════
# 输出 Schemas（Response Body）
# ═══════════════════════════════════════

class CostOut(BaseModel):
    """成本记录输出"""
    id: int
    product_plan_id: str
    cost_type: str
    item_name: Optional[str]
    target_value: Optional[float]
    actual_value: Optional[float]
    currency: str
    remark: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    """策划基础输出"""
    id: str
    name: str
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None
    target_market_detail: Optional[str] = None
    # ---- 现有字段 ----
    status: str
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    project_links_count: int = 0

    class Config:
        from_attributes = True


class PlanStatusOut(BaseModel):
    """流程状态输出"""
    id: str
    current_stage: str
    current_stage_label: str
    stages: list[dict]
    progress_pct: int


class NextActionOut(BaseModel):
    """下一步动作引导输出"""
    current_stage: str
    next_stage: Optional[str]
    next_action: str
    missing_fields: list[str]
    can_advance: bool


T = TypeVar("T")


class PaginatedResult(BaseModel, Generic[T]):
    """分页结果"""
    items: list[T]
    total: int
    page: int
    page_size: int


class PlanDetailOut(PlanOut):
    """策划详情（含 costs + 子表数据）"""
    costs: list[CostOut] = []
    project_links: list[ProductPlanLinkOut] = []
    initiation: Optional[_InitiationOut] = None
    market_info: Optional[_MarketOut] = None
    tech_spec: Optional[_TechSpecOut] = None
    team_members: list[_TeamOut] = []


# ═══════════════════════════════════════
# 批量操作 Schemas
# ═══════════════════════════════════════

class BatchCloneRequest(BaseModel):
    """批量克隆策划请求"""
    plan_ids: list[str]


class TemplateBatchItem(BaseModel):
    """模板批量创建条目"""
    template_id: str
    count: int = 1


class BatchCreateRequest(BaseModel):
    """按模板批量创建策划请求"""
    templates: list[TemplateBatchItem]


# ═══════════════════════════════════════
# 阶段常量
# ═══════════════════════════════════════

_STAGE_ORDER = [
    ProductPlanStage.DRAFT,
    ProductPlanStage.COMPETITOR,
    ProductPlanStage.DEFINITION,
    ProductPlanStage.COSTING,
    ProductPlanStage.TECH_INPUT,
    ProductPlanStage.PROJECT_INIT,
    ProductPlanStage.APPROVED,
    ProductPlanStage.RELEASED,
]


# ═══════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════

def _plan_to_dict(plan: ProductPlan) -> dict:
    """将 ProductPlan ORM 对象转为响应 dict"""
    return {
        "id": plan.id,
        "name": plan.name,
        "series": plan.series,
        "market": plan.market,
        "competitor_id": plan.competitor_id,
        "cost_target": plan.cost_target,
        "performance_target": plan.performance_target,
        # ---- 子表字段（通过 initiation 访问）----
        "product_type": plan.initiation.product_type if plan.initiation else None,
        "target_market_detail": plan.target_market_detail,
        "climate_zone": plan.initiation.climate_zone if plan.initiation else None,
        "refrigerant": plan.initiation.refrigerant if plan.initiation else None,
        "capacity_range": plan.initiation.capacity_range if plan.initiation else None,
        "voltage_freq": plan.initiation.voltage_freq if plan.initiation else None,
        "series_name": plan.initiation.series_name if plan.initiation else None,
        "energy_rating": plan.initiation.energy_rating if plan.initiation else None,
        "dev_category": plan.initiation.dev_category if plan.initiation else None,
        "project_origin": plan.initiation.project_origin if plan.initiation else None,
        "project_duration": plan.initiation.project_duration if plan.initiation else None,
        "ip_ownership": plan.initiation.ip_ownership if plan.initiation else None,
        # ---- 现有字段 ----
        "status": plan.status.value if plan.status else "draft",
        "created_by": plan.created_by,
        "created_at": str(plan.created_at) if plan.created_at else None,
        "updated_at": str(plan.updated_at) if plan.updated_at else None,
        "project_links_count": len(plan.project_links) if plan.project_links else 0,
    }


def _cost_to_dict(c: Cost) -> dict:
    """将 Cost ORM 对象转为响应 dict"""
    return {
        "id": c.id,
        "product_plan_id": c.product_plan_id,
        "cost_type": c.cost_type.value if c.cost_type else "target",
        "item_name": c.item_name,
        "target_value": c.target_value,
        "actual_value": c.actual_value,
        "currency": c.currency,
        "remark": c.remark,
        "created_at": str(c.created_at) if c.created_at else None,
    }


def _orm_to_dict(obj) -> Optional[dict]:
    """将单个 ORM 对象转为扁平 dict"""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _build_stage_list(current: ProductPlanStage) -> list[dict]:
    """构建阶段状态列表（供前端进度条使用）"""
    stages = []
    for i, s in enumerate(_STAGE_ORDER):
        label = STAGE_LABELS.get(s, s.value)
        idx = _STAGE_ORDER.index(current) if current in _STAGE_ORDER else 0
        stages.append({
            "key": s.value,
            "label": label,
            "status": "completed" if i < idx else ("active" if i == idx else "pending"),
        })
    return stages
