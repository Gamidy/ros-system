"""冷量联动成本重算 API — CapacityUnitCost CRUD + 重算触发 + 查询

端点：
  GET/POST    /api/cost-recalc/capacity-costs       — 冷量段单价CRUD
  PUT/DELETE  /api/cost-recalc/capacity-costs/{id}
  POST        /api/cost-recalc/run                   — 手动触发冷量重算
  GET         /api/cost-recalc/results               — 重算结果列表
  GET         /api/cost-recalc/results/{id}           — 重算结果详情
  GET         /api/cost-recalc/results/by-plan/{plan_id} — 按产品查询历史
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.capacity_unit_cost import CapacityUnitCost
from app.models.cost_recalculation import (
    CostRecalculationResult, CostRecalculationItem, RecalcStatus,
)
from app.services.capacity_recalc_service import run_capacity_recalculation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost-recalc", tags=["cost-recalculation"])

_RECALC_DEP = Depends(require_menu("cost-accounting"))


# ═══════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════

class CapacityCostCreate(BaseModel):
    capacity_key: str = Field(..., max_length=20, description="冷量段标识，如'22K'")
    btu: int = Field(..., ge=1000, description="BTU值, 如22000")
    unit_cost_w: float = Field(..., ge=0, description="单价(万元), 如0.178")


class CapacityCostOut(BaseModel):
    id: int
    capacity_key: str
    btu: int
    unit_cost_w: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecalcRunRequest(BaseModel):
    product_plan_id: str
    period_id: Optional[int] = None
    sheet_id: Optional[int] = None


class RecalcItemOut(BaseModel):
    id: int
    dimension: str
    item_name: str
    baseline_amount: float
    actual_amount: float
    variance: float
    variance_pct: float
    remark: Optional[str] = None

    class Config:
        from_attributes = True


class RecalcResultOut(BaseModel):
    id: int
    product_plan_id: str
    period_id: Optional[int] = None
    sheet_id: Optional[int] = None
    main_capacity: Optional[str] = None
    matched_btu: Optional[int] = None
    capacity_key: Optional[str] = None
    baseline_material_cost: float = 0
    complexity_factor: float = 1.0
    actual_bom_cost: float = 0
    bom_id: Optional[int] = None
    bom_no: Optional[str] = None
    variance_amount: float = 0
    variance_pct: float = 0
    cost_efficiency_score: float = 0
    status: str = "completed"
    trigger_source: str = "manual"
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    remark: Optional[str] = None
    items: List[RecalcItemOut] = []

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════
# CapacityUnitCost CRUD
# ═══════════════════════════════════════════

@router.get("/capacity-costs", response_model=List[CapacityCostOut])
def list_capacity_costs(db: Session = Depends(get_db), _=_RECALC_DEP):
    """获取冷量段单价列表（按 BTU 排序）"""
    return db.query(CapacityUnitCost).order_by(CapacityUnitCost.btu).all()


@router.post("/capacity-costs", response_model=CapacityCostOut)
def create_capacity_cost(
    data: CapacityCostCreate,
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """新增冷量段单价"""
    existing = db.query(CapacityUnitCost).filter(
        CapacityUnitCost.btu == data.btu
    ).first()
    if existing:
        raise HTTPException(400, f"BTU={data.btu} 的冷量段已存在")
    item = CapacityUnitCost(
        capacity_key=data.capacity_key,
        btu=data.btu,
        unit_cost_w=data.unit_cost_w,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/capacity-costs/{cid}", response_model=CapacityCostOut)
def update_capacity_cost(
    cid: int,
    data: CapacityCostCreate,
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """更新冷量段单价"""
    item = db.query(CapacityUnitCost).filter(CapacityUnitCost.id == cid).first()
    if not item:
        raise HTTPException(404, "冷量段不存在")
    item.capacity_key = data.capacity_key
    item.btu = data.btu
    item.unit_cost_w = data.unit_cost_w
    db.commit()
    db.refresh(item)
    return item


@router.delete("/capacity-costs/{cid}")
def delete_capacity_cost(
    cid: int,
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """删除冷量段单价"""
    item = db.query(CapacityUnitCost).filter(CapacityUnitCost.id == cid).first()
    if not item:
        raise HTTPException(404, "冷量段不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ═══════════════════════════════════════════
# 冷量联动重算
# ═══════════════════════════════════════════

@router.post("/run")
def trigger_recalculation(
    data: RecalcRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发冷量联动重算"""
    result = run_capacity_recalculation(
        product_plan_id=data.product_plan_id,
        period_id=data.period_id,
        sheet_id=data.sheet_id,
        trigger_source="manual",
        user_name=current_user.username,
        db=db,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "重算失败"))
    return result


@router.get("/results", response_model=List[RecalcResultOut])
def list_recalc_results(
    plan_id: Optional[str] = Query(None),
    period_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """重算结果列表"""
    q = db.query(CostRecalculationResult)
    if plan_id:
        q = q.filter(CostRecalculationResult.product_plan_id == plan_id)
    if period_id:
        q = q.filter(CostRecalculationResult.period_id == period_id)
    if status:
        q = q.filter(CostRecalculationResult.status == status)
    return q.order_by(desc(CostRecalculationResult.created_at)).limit(limit).all()


@router.get("/results/{rid}", response_model=RecalcResultOut)
def get_recalc_result(
    rid: int,
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """重算结果详情（含明细）"""
    result = db.query(CostRecalculationResult).filter(
        CostRecalculationResult.id == rid
    ).first()
    if not result:
        raise HTTPException(404, "重算结果不存在")
    result.items = db.query(CostRecalculationItem).filter(
        CostRecalculationItem.result_id == rid
    ).all()
    return result


@router.get("/results/by-plan/{plan_id}", response_model=List[RecalcResultOut])
def get_recalc_results_by_plan(
    plan_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """按产品策划查询历史重算结果"""
    return db.query(CostRecalculationResult).filter(
        CostRecalculationResult.product_plan_id == plan_id
    ).order_by(desc(CostRecalculationResult.created_at)).limit(limit).all()


@router.get("/low-efficiency")
def get_low_efficiency_products(
    min_score: float = Query(60, ge=0, le=100, description="效率评分上限（低于此值视为低效率）"),
    max_results: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _=_RECALC_DEP,
):
    """查询低效率产品列表（最新一次重算效率评分低于阈值的）"""
    from sqlalchemy import func as sa_func

    # 取每个产品的最新一次 completed 重算结果
    subq = (
        db.query(
            CostRecalculationResult.product_plan_id,
            sa_func.max(CostRecalculationResult.id).label("max_id"),
        )
        .filter(CostRecalculationResult.status == RecalcStatus.COMPLETED)
        .group_by(CostRecalculationResult.product_plan_id)
        .subquery()
    )

    results = (
        db.query(CostRecalculationResult)
        .join(
            subq,
            CostRecalculationResult.id == subq.c.max_id,
        )
        .filter(CostRecalculationResult.cost_efficiency_score < min_score)
        .order_by(CostRecalculationResult.cost_efficiency_score.asc())
        .limit(max_results)
        .all()
    )

    return [
        {
            "id": r.id,
            "product_plan_id": r.product_plan_id,
            "main_capacity": r.main_capacity,
            "capacity_key": r.capacity_key,
            "baseline_material_cost": r.baseline_material_cost,
            "actual_bom_cost": r.actual_bom_cost,
            "variance_amount": r.variance_amount,
            "variance_pct": r.variance_pct,
            "cost_efficiency_score": r.cost_efficiency_score,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in results
    ]
