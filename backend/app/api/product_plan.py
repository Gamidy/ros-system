"""ProductPlan API — 产品策划 CRUD + 流程推进

6个端点：
- POST /product-plans — 创建策划
- GET /product-plans — 列表（分页+筛选）
- GET /product-plans/{id} — 详情
- GET /product-plans/{id}/status — 流程状态
- POST /product-plans/{id}/advance — 推进流程
- GET /product-plans/{id}/next-action — 下一步引导
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan, ProductPlanStage, Cost, CostType, BOMType
from app.services.product_plan_workflow import (
    create_product_plan as workflow_create,
    advance_stage as workflow_advance,
    get_next_action as workflow_next_action,
    STAGE_LABELS,
)

router = APIRouter(prefix="/product-plans", tags=["产品策划"])


# ── Schemas ──

class CostCreate(BaseModel):
    cost_type: str = "target"
    item_name: Optional[str] = None
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    currency: str = "CNY"
    remark: Optional[str] = None


class CostOut(BaseModel):
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


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None


class PlanOut(BaseModel):
    id: str
    name: str
    series: Optional[str]
    market: Optional[str]
    competitor_id: Optional[int]
    cost_target: Optional[str]
    performance_target: Optional[str]
    status: str
    project_id: Optional[int]
    created_by: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class PlanStatusOut(BaseModel):
    id: str
    current_stage: str
    current_stage_label: str
    stages: list[dict]
    progress_pct: int


class NextActionOut(BaseModel):
    current_stage: str
    next_stage: Optional[str]
    next_action: str
    missing_fields: list[str]
    can_advance: bool


# ── 辅助函数 ──

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
        "status": plan.status.value if plan.status else "draft",
        "project_id": plan.project_id,
        "created_by": plan.created_by,
        "created_at": str(plan.created_at) if plan.created_at else None,
        "updated_at": str(plan.updated_at) if plan.updated_at else None,
    }


def _cost_to_dict(c: Cost) -> dict:
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


# ── API 端点 ──

@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
):
    """创建产品策划（DRAFT）"""
    plan = workflow_create(db, data.model_dump(), current_user.username)
    return _plan_to_dict(plan)


@router.get("")
def list_plans(
    status: Optional[str] = Query(None, description="按状态筛选"),
    series: Optional[str] = Query(None, description="按系列筛选"),
    search: Optional[str] = Query(None, description="名称搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """产品策划列表（分页+筛选）"""
    q = db.query(ProductPlan)

    if status:
        try:
            s = ProductPlanStage(status)
            q = q.filter(ProductPlan.status == s)
        except ValueError:
            pass
    if series:
        q = q.filter(ProductPlan.series.ilike(f"%{series}%"))
    if search:
        q = q.filter(ProductPlan.name.ilike(f"%{search}%"))

    total = q.count()
    plans = q.order_by(ProductPlan.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_plan_to_dict(p) for p in plans],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{plan_id}")
def get_plan_detail(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """策划详情（含 costs 列表）"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    result = _plan_to_dict(plan)
    result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
    return result


@router.get("/{plan_id}/status", response_model=PlanStatusOut)
def get_plan_status(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """流程状态详情"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    current = plan.status
    stages = _build_stage_list(current)
    idx = _STAGE_ORDER.index(current) if current in _STAGE_ORDER else 0
    progress_pct = round((idx / (len(_STAGE_ORDER) - 1)) * 100) if len(_STAGE_ORDER) > 1 else 0

    return {
        "id": plan.id,
        "current_stage": current.value if current else "draft",
        "current_stage_label": STAGE_LABELS.get(current, "未知"),
        "stages": stages,
        "progress_pct": progress_pct,
    }


@router.post("/{plan_id}/advance")
def advance_plan_stage(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
):
    """推进策划流程"""
    plan = workflow_advance(db, plan_id, current_user.username)
    result = _plan_to_dict(plan)
    result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
    if plan.project_id:
        result["project_id"] = plan.project_id
    return result


@router.get("/{plan_id}/next-action", response_model=NextActionOut)
def get_next_action(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """获取下一步动作引导"""
    return workflow_next_action(db, plan_id)


@router.patch("/{plan_id}")
def update_plan(
    plan_id: str,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
):
    """更新策划基本信息"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None and hasattr(plan, key):
            setattr(plan, key, val)
    plan.updated_at = func.now()
    db.commit()
    db.refresh(plan)
    return _plan_to_dict(plan)


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """删除产品策划"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    db.delete(plan)
    db.commit()
    return {"ok": True}


# ── Cost 子资源 ──

@router.post("/{plan_id}/costs")
def create_cost(
    plan_id: str,
    data: CostCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """添加成本记录"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    try:
        ct = CostType(data.cost_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效成本类型: {data.cost_type}")

    cost = Cost(
        product_plan_id=plan_id,
        cost_type=ct,
        item_name=data.item_name,
        target_value=data.target_value,
        actual_value=data.actual_value,
        currency=data.currency or "CNY",
        remark=data.remark,
    )
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return _cost_to_dict(cost)


@router.delete("/{plan_id}/costs/{cost_id}")
def delete_cost(
    plan_id: str,
    cost_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """删除成本记录"""
    cost = db.query(Cost).filter(Cost.id == cost_id, Cost.product_plan_id == plan_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="成本记录不存在")
    db.delete(cost)
    db.commit()
    return {"ok": True}
