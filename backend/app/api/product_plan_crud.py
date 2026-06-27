"""ProductPlan CRUD API — 核心增删改查端点

从 product_plan.py 提取 CRUD 端点到独立模块。
路由 prefix 由 main.py 统一管理: include_router(..., prefix="/api/product-plans")

包含端点：
  POST   ""                     — create_plan
  GET    ""                     — list_plans
  GET    "/{plan_id}"           — get_plan_detail
  GET    "/{plan_id}/status"    — get_plan_status
  PATCH  "/{plan_id}"           — update_plan
  DELETE "/{plan_id}"           — delete_plan
  POST   "/validate"            — validate_plan_data
  POST   "/{plan_id}/costs"     — create_cost
  DELETE "/{plan_id}/costs/{cost_id}" — delete_cost
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan, ProductPlanStage, Cost, CostType
from app.api.product_plan_schemas import (
    CostCreate,
    CostOut,
    PlanCreate,
    PlanUpdate,
    PlanOut,
    PlanStatusOut,
    PlanDetailOut,
    _plan_to_dict,
    _cost_to_dict,
    _build_stage_list,
    _STAGE_ORDER,
)
from app.api.product_plan_subs import (
    InitiationOut as _InitiationOut,
    MarketOut as _MarketOut,
    TechSpecOut as _TechSpecOut,
    TeamOut as _TeamOut,
)
from app.services.product_plan_workflow import (
    create_product_plan as workflow_create,
    STAGE_LABELS,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["产品策划CRUD"])


# =====================================================================
#  辅助函数 / Helpers
# =====================================================================

def _get_plan_or_404(db: Session, plan_id: str) -> ProductPlan:
    """按 ID 获取策划，不存在则 404"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    return plan


def _orm_to_dict(obj) -> Optional[dict]:
    """将单个 ORM 对象转为扁平 dict"""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# =====================================================================
#  POST "" — create_plan
# =====================================================================

@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
):
    """创建产品策划（初始状态为 DRAFT）

    通过 product_plan_workflow 创建工作流实例。
    """
    plan = workflow_create(db, data.model_dump(), current_user.username)
    return _plan_to_dict(plan)


# =====================================================================
#  GET "" — list_plans (分页 + 筛选)
# =====================================================================

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
    """产品策划列表（分页 + 筛选）"""
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
    plans = (
        q.order_by(ProductPlan.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_plan_to_dict(p) for p in plans],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# =====================================================================
#  GET "/{plan_id}" — get_plan_detail (含 costs + 子表数据)
# =====================================================================

@router.get("/{plan_id}", response_model=PlanDetailOut)
def get_plan_detail(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """策划详情（含成本记录 + 子表数据：立项、市场、技术规格、团队）"""
    plan = _get_plan_or_404(db, plan_id)

    result = _plan_to_dict(plan)
    result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
    result["initiation"] = _orm_to_dict(plan.initiation)
    result["market_info"] = _orm_to_dict(plan.market_info)
    result["tech_spec"] = _orm_to_dict(plan.tech_spec)
    result["team_members"] = [_orm_to_dict(m) for m in (plan.team_members or [])]
    return result


# =====================================================================
#  GET "/{plan_id}/status" — get_plan_status (流程状态)
# =====================================================================

@router.get("/{plan_id}/status", response_model=PlanStatusOut)
def get_plan_status(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """策划流程状态详情（含阶段列表 + 进度百分比）"""
    plan = _get_plan_or_404(db, plan_id)

    current = plan.status
    stages = _build_stage_list(current)
    idx = _STAGE_ORDER.index(current) if current in _STAGE_ORDER else 0
    progress_pct = (
        round((idx / (len(_STAGE_ORDER) - 1)) * 100)
        if len(_STAGE_ORDER) > 1
        else 0
    )

    return {
        "id": plan.id,
        "current_stage": current.value if current else "draft",
        "current_stage_label": STAGE_LABELS.get(current, "未知"),
        "stages": stages,
        "progress_pct": progress_pct,
    }


# =====================================================================
#  PATCH "/{plan_id}" — update_plan
# =====================================================================

@router.patch("/{plan_id}")
def update_plan(
    plan_id: str,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
):
    """更新策划基本信息（部分更新）"""
    plan = _get_plan_or_404(db, plan_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None and hasattr(plan, key):
            setattr(plan, key, val)
    plan.updated_at = func.now()
    db.commit()
    db.refresh(plan)
    return _plan_to_dict(plan)


# =====================================================================
#  DELETE "/{plan_id}" — delete_plan
# =====================================================================

@router.delete("/{plan_id}")
def delete_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """删除产品策划"""
    plan = _get_plan_or_404(db, plan_id)
    db.delete(plan)
    db.commit()
    return {"ok": True}


# =====================================================================
#  POST "/validate" — validate_plan_data (数据验证)
# =====================================================================

@router.post("/validate")
def validate_plan_data(
    data: PlanCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """验证产品策划数据完整性

    在正式创建前检查必填字段、格式和业务约束。
    返回验证结果及详细错误列表。
    """
    errors = []

    # 名称字段验证
    if not data.name or not data.name.strip():
        errors.append({"field": "name", "message": "策划名称不能为空"})
    elif len(data.name) > 200:
        errors.append({"field": "name", "message": "策划名称不能超过200个字符"})

    # series 长度验证
    if data.series and len(data.series) > 100:
        errors.append({"field": "series", "message": "系列名称不能超过100个字符"})

    # market 长度验证
    if data.market and len(data.market) > 100:
        errors.append({"field": "market", "message": "目标市场不能超过100个字符"})

    # competitor_id 存在性验证
    if data.competitor_id is not None:
        from app.models.competitor import Competitor
        exists = db.query(Competitor).filter(Competitor.id == data.competitor_id).first()
        if not exists:
            errors.append({
                "field": "competitor_id",
                "message": f"竞争对手 ID={data.competitor_id} 不存在",
            })

    # cost_target 格式提示
    if data.cost_target and len(data.cost_target) > 500:
        errors.append({"field": "cost_target", "message": "成本目标不能超过500个字符"})

    # performance_target 格式提示
    if data.performance_target and len(data.performance_target) > 500:
        errors.append({"field": "performance_target", "message": "性能目标不能超过500个字符"})

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "summary": "数据验证通过" if is_valid else f"发现 {len(errors)} 个问题",
    }


# =====================================================================
#  POST "/{plan_id}/costs" — create_cost
# =====================================================================

@router.post("/{plan_id}/costs")
def create_cost(
    plan_id: str,
    data: CostCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """添加成本记录到策划"""
    _get_plan_or_404(db, plan_id)

    try:
        ct = CostType(data.cost_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效成本类型: {data.cost_type}",
        )

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


# =====================================================================
#  DELETE "/{plan_id}/costs/{cost_id}" — delete_cost
# =====================================================================

@router.delete("/{plan_id}/costs/{cost_id}")
def delete_cost(
    plan_id: str,
    cost_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """删除策划下的成本记录"""
    cost = (
        db.query(Cost)
        .filter(Cost.id == cost_id, Cost.product_plan_id == plan_id)
        .first()
    )
    if not cost:
        raise HTTPException(status_code=404, detail="成本记录不存在")
    db.delete(cost)
    db.commit()
    return {"ok": True}
