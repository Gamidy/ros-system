"""ProductPlan API — 产品策划 CRUD + 流程推进

6个端点 + 集成子表数据：
- POST /product-plans — 创建策划
- GET /product-plans — 列表（分页+筛选）
- GET /product-plans/{id} — 详情（含 costs + 子表数据）
- GET /product-plans/{id}/status — 流程状态
- POST /product-plans/{id}/advance — 推进流程
- GET /product-plans/{id}/next-action — 下一步引导
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar
import json
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan, ProductPlanStage, Cost, CostType, BOMType, ProductPlanProjectLink, ProductPlanHistory
from app.schemas.product_plan_link import ProductPlanLinkOut
from app.models.product_plan_subs import (
    ProductPlanInitiation,
    ProductPlanMarket,
    ProductPlanTechSpec,
    ProductPlanTeam,
)
from app.services.product_plan_workflow import (
    create_product_plan as workflow_create,
    advance_stage as workflow_advance,
    get_next_action as workflow_next_action,
    STAGE_LABELS,
)
from app.services.plan_validator import validate_plan as run_validation

router = APIRouter(prefix="/product-plans", tags=["产品策划"])

# P4复盘路由
from app.api.product_plan_review import router as review_router
__all__ = ["router", "review_router"]


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
    # [P0-2] 创建策划字段对齐
    product_type: Optional[str] = None
    market_id: Optional[str] = None


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
    name: Optional[str] = None
    series: Optional[str] = None
    market: Optional[str] = None
    competitor_id: Optional[int] = None
    cost_target: Optional[str] = None
    performance_target: Optional[str] = None


class PlanOut(BaseModel):
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


T = TypeVar("T")


class PaginatedResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ── 子表 Schemas（引用自 product_plan_subs）──

from app.api.product_plan_subs import (
    InitiationOut as _InitiationOut,
    MarketOut as _MarketOut,
    TechSpecOut as _TechSpecOut,
    TeamOut as _TeamOut,
)


class PlanDetailOut(PlanOut):
    """策划详情（含 costs + 子表数据）"""
    costs: list[CostOut] = []
    project_links: list[ProductPlanLinkOut] = []
    initiation: Optional[_InitiationOut] = None
    market_info: Optional[_MarketOut] = None
    tech_spec: Optional[_TechSpecOut] = None
    team_members: list[_TeamOut] = []


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
) -> PlanOut:
    """创建产品策划（DRAFT）"""
    try:
        plan = workflow_create(db, data.model_dump(), current_user.username)
        return _plan_to_dict(plan)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建策划失败: {str(e)}")


@router.get("")
def list_plans(
    status: Optional[str] = Query(None, description="按状态筛选"),
    series: Optional[str] = Query(None, description="按系列筛选"),
    search: Optional[str] = Query(None, description="名称搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> PaginatedResult[PlanOut]:
    """产品策划列表（分页+筛选）"""
    try:
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
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"查询策划列表失败: {str(e)}")


@router.get("/{plan_id}", response_model=PlanDetailOut)
def get_plan_detail(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> PlanDetailOut:
    """策划详情（含 costs + 子表数据）"""
    # [P0-1] N+1 修复: 使用 selectinload 预加载所有关联
    plan = db.query(ProductPlan).options(
        selectinload(ProductPlan.costs),
        selectinload(ProductPlan.project_links),
        selectinload(ProductPlan.initiation),
        selectinload(ProductPlan.market_info),
        selectinload(ProductPlan.tech_spec),
        selectinload(ProductPlan.team_members),
    ).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    result = _plan_to_dict(plan)
    result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
    result["project_links"] = [
        ProductPlanLinkOut.model_validate(link)
        for link in (plan.project_links or [])
    ]
    result["initiation"] = _orm_to_dict(plan.initiation)
    result["market_info"] = _orm_to_dict(plan.market_info)
    result["tech_spec"] = _orm_to_dict(plan.tech_spec)
    result["team_members"] = [_orm_to_dict(m) for m in (plan.team_members or [])]
    return result


@router.get("/{plan_id}/status", response_model=PlanStatusOut)
def get_plan_status(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> PlanStatusOut:
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
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """推进策划流程（[P0-3] 支持审批意见参数）"""
    plan = workflow_advance(db, plan_id, current_user.username, comment=req.comment)
    result = _plan_to_dict(plan)
    result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
    # 已关联项目通过 project_links 获取
    result["project_links"] = [ProductPlanLinkOut.model_validate(l) for l in (plan.project_links or [])]
    return result


@router.post("/{plan_id}/approve")
def approve_plan(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """通过产品策划审批。

    将策划推进至 APPROVED 阶段，同时创建审批请求记录。
    仅允许在 PROJECT_INIT 阶段的策划执行此操作。

    Args:
        plan_id: 策划 ID（路径参数）
        req: 审批请求体，包含 comment 审批意见

    Returns:
        dict: 更新后的策划详情，包含 costs 和 project_links

    Raises:
        HTTPException 404: 策划不存在
        HTTPException 400: 当前阶段不允许审批操作
        HTTPException 500: 审批操作失败（内部错误）
    """
    try:
        plan = workflow_advance(db, plan_id, current_user.username, comment=req.comment)
        result = _plan_to_dict(plan)
        result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
        result["project_links"] = [ProductPlanLinkOut.model_validate(l) for l in (plan.project_links or [])]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审批操作失败: {str(e)}")


@router.post("/{plan_id}/reject")
def reject_plan(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """驳回产品策划。

    将策划退回至 DEFINITION 阶段。
    仅允许在 PROJECT_INIT 阶段的策划执行此操作。

    Args:
        plan_id: 策划 ID（路径参数）
        req: 驳回请求体，包含 comment 驳回意见

    Returns:
        dict: 更新后的策划基本信息

    Raises:
        HTTPException 404: 策划不存在
        HTTPException 400: 当前阶段不可驳回（仅 PROJECT_INIT 允许）
        HTTPException 500: 驳回操作失败（内部错误）
    """
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        if plan.status != ProductPlanStage.PROJECT_INIT:
            raise HTTPException(
                status_code=400,
                detail=f"当前阶段「{STAGE_LABELS.get(plan.status, plan.status.value)}」不可驳回，仅 PROJECT_INIT 阶段允许驳回",
            )

        plan.status = ProductPlanStage.DEFINITION
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"驳回操作失败: {str(e)}")


@router.post("/{plan_id}/withdraw")
def withdraw_plan(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """撤回产品策划。

    将策划退回至 DRAFT 阶段。
    已批准（APPROVED）或已发布（RELEASED）的策划不可撤回。

    Args:
        plan_id: 策划 ID（路径参数）
        req: 撤回请求体，包含 comment 撤回说明

    Returns:
        dict: 更新后的策划基本信息

    Raises:
        HTTPException 404: 策划不存在
        HTTPException 400: 当前阶段不可撤回（APPROVED/RELEASED 阶段）
        HTTPException 500: 撤回操作失败（内部错误）
    """
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        if plan.status in (ProductPlanStage.APPROVED, ProductPlanStage.RELEASED):
            raise HTTPException(
                status_code=400,
                detail=f"当前阶段「{STAGE_LABELS.get(plan.status, plan.status.value)}」不可撤回",
            )

        plan.status = ProductPlanStage.DRAFT
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"撤回操作失败: {str(e)}")


@router.patch("/{plan_id}/stage")
def set_plan_stage(
    plan_id: str,
    data: SetStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """直接设置策划阶段。

    将策划手动设置为指定的目标阶段。此操作直接修改数据库中的 status 字段。
    仅 admin 和 general_manager 角色可执行此操作。

    Args:
        plan_id: 策划 ID（路径参数）
        data: 设置请求体，包含 target stage 值

    Returns:
        dict: 更新后的策划详情，包含 costs 和 project_links

    Raises:
        HTTPException 403: 当前用户无权限（非 admin 或 general_manager）
        HTTPException 404: 策划不存在
        HTTPException 400: 无效的阶段值
        HTTPException 500: 设置阶段失败（内部错误）
    """
    try:
        if current_user.role not in ("admin", "general_manager"):
            raise HTTPException(status_code=403, detail="仅管理员和总经理可执行此操作")

        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        try:
            new_stage = ProductPlanStage(data.stage)
        except ValueError:
            valid = [s.value for s in ProductPlanStage]
            raise HTTPException(status_code=400, detail=f"无效阶段值: {data.stage}，有效值: {', '.join(valid)}")

        plan.status = new_stage
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)

        result = _plan_to_dict(plan)
        result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
        result["project_links"] = [ProductPlanLinkOut.model_validate(l) for l in (plan.project_links or [])]
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"设置阶段失败: {str(e)}")


@router.get("/{plan_id}/next-action", response_model=NextActionOut)
def get_next_action(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> NextActionOut:
    """获取下一步动作引导"""
    return workflow_next_action(db, plan_id)


@router.patch("/{plan_id}")
def update_plan(
    plan_id: str,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """更新策划基本信息"""
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        # [P1-2] 数据级权限: 非管理员只能编辑自己创建的策划
        if current_user.role not in ("admin", "general_manager") and plan.created_by != current_user.username:
            raise HTTPException(status_code=403, detail="只能编辑自己创建的策划")

        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if val is not None and hasattr(plan, key):
                setattr(plan, key, val)
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新策划失败: {str(e)}")


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """删除产品策划"""
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        # [P1-2] 数据级权限: 非管理员只能删除自己创建的策划
        if current_user.role not in ("admin", "general_manager") and plan.created_by != current_user.username:
            raise HTTPException(status_code=403, detail="只能删除自己创建的策划")

        # 级联删除关联子表记录
        db.query(ProductPlanTeam).filter(ProductPlanTeam.product_plan_id == plan_id).delete()
        db.query(Cost).filter(Cost.product_plan_id == plan_id).delete()
        db.query(ProductPlanInitiation).filter(ProductPlanInitiation.product_plan_id == plan_id).delete()
        db.query(ProductPlanMarket).filter(ProductPlanMarket.product_plan_id == plan_id).delete()
        db.query(ProductPlanTechSpec).filter(ProductPlanTechSpec.product_plan_id == plan_id).delete()
        db.query(ProductPlanProjectLink).filter(ProductPlanProjectLink.product_plan_id == plan_id).delete()
        db.query(ProductPlanHistory).filter(ProductPlanHistory.product_plan_id == plan_id).delete()

        db.delete(plan)
        db.commit()
        return {"ok": True}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除策划失败: {str(e)}")


# ── 校验端点 ──


@router.post("/validate")
def validate_plan_data(
    data: PlanValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """校验策划数据完整性（提交前调用）

    从数据库读取校验规则配置，对 plan_data 逐条执行。
    返回 {valid: bool, errors: [{field, message}]}
    """
    try:
        plan_data = data.model_dump(exclude_unset=True)
        result = run_validation(plan_data, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"校验执行失败: {str(e)}")


# ── Cost 子资源 ──

@router.post("/{plan_id}/costs")
def create_cost(
    plan_id: str,
    data: CostCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """添加成本记录"""
    try:
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
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加成本记录失败: {str(e)}")


@router.delete("/{plan_id}/costs/{cost_id}")
def delete_cost(
    plan_id: str,
    cost_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """删除成本记录"""
    cost = db.query(Cost).filter(Cost.id == cost_id, Cost.product_plan_id == plan_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="成本记录不存在")
    db.delete(cost)
    db.commit()
    return {"ok": True}


# ── 版本历史端点 ──


@router.get("/{plan_id}/versions")
def list_plan_versions(
    plan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """产品策划版本历史列表

    返回该策划的所有历史版本记录（分页），按版本号降序排列。
    当前最新版本可通过 GET /product-plans/{id} 获取。
    """
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    try:
        q = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id
        ).order_by(ProductPlanHistory.version.desc())

        total = q.count()
        versions = q.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [
                {
                    "version": v.version,
                    "changed_by": v.changed_by,
                    "changed_at": str(v.changed_at) if v.changed_at else None,
                }
                for v in versions
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "current_version": plan.version,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"查询版本历史失败: {str(e)}")


@router.get("/{plan_id}/versions/{version}")
def get_plan_version_snapshot(
    plan_id: str,
    version: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取策划指定版本的完整数据快照"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    try:
        history = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id,
            ProductPlanHistory.version == version,
        ).first()

        if not history:
            raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")

        snapshot = json.loads(history.snapshot)
        return {
            "version": history.version,
            "snapshot": snapshot,
            "changed_by": history.changed_by,
            "changed_at": str(history.changed_at) if history.changed_at else None,
        }
    except HTTPException:
        raise
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"快照数据解析失败: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"查询版本快照失败: {str(e)}")
