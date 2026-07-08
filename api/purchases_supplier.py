"""采购订单 API — 供应商管理模块"""
from datetime import date, datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_menu, require_role
from app.models.purchase import Supplier, SupplierEvaluation, VALID_DIMENSIONS, DIMENSION_LABELS
from app.schemas import (
    SupplierCreate, SupplierOut, SupplierUpdate,
    EvaluationCreate, EvaluationOut, SupplierStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchases", tags=["采购订单管理-供应商"])


# ══════════════════════════════════════════════════
# Suppliers
# ══════════════════════════════════════════════════

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    keyword: str = "",
    status: str = "",
    category: str = "",
    sort_by: str = "overall_score",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    _=Depends(require_menu("purchases")),
) -> list[SupplierOut]:
    """列出所有供应商，支持关键词/状态/品类筛选和排序"""
    q = db.query(Supplier).filter(Supplier.is_deleted == 0)
    if keyword:
        q = q.filter(
            Supplier.name.like(f"%{keyword}%") |
            Supplier.code.like(f"%{keyword}%") |
            Supplier.contact.like(f"%{keyword}%")
        )
    if status:
        q = q.filter(Supplier.status == status)
    if category:
        q = q.filter(Supplier.category == category)
    # 排序
    sort_col = getattr(Supplier, sort_by, Supplier.overall_score)
    if sort_order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())
    return q.all()


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> SupplierOut:
    """创建供应商 — code全局唯一"""
    if db.query(Supplier).filter(Supplier.code == data.code).first():
        raise HTTPException(status_code=400, detail="供应商编码已存在")
    s = Supplier(**data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s


# ══════════════════════════════════════════════════
# 供应商详情/删除
# ══════════════════════════════════════════════════


@router.get("/suppliers/{sid}", response_model=SupplierOut)
def get_supplier(sid: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))) -> SupplierOut:
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    return s


@router.patch("/suppliers/{sid}", response_model=SupplierOut)
def update_supplier(sid: int, data: SupplierUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> SupplierOut:
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "code" in updates and updates["code"] != s.code:
        if db.query(Supplier).filter(Supplier.code == updates["code"], Supplier.id != sid, Supplier.is_deleted == 0).first():
            raise HTTPException(400, f"编码 '{updates['code']}' 已被使用")
    for k, v in updates.items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    return s


@router.delete("/suppliers/{sid}")
def delete_supplier(sid: int, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> dict:
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    s.is_deleted = 1
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
# 供应商评估
# ══════════════════════════════════════════════════


@router.get("/suppliers/{sid}/evaluations", response_model=list[EvaluationOut])
def list_evaluations(sid: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    evals = db.query(SupplierEvaluation).filter(SupplierEvaluation.supplier_id == sid).order_by(SupplierEvaluation.evaluated_at.desc()).all()
    return [EvaluationOut(id=e.id, supplier_id=e.supplier_id, dimension=e.dimension, dimension_label=DIMENSION_LABELS.get(e.dimension, e.dimension), score=e.score, weight=e.weight, comment=e.comment, evaluator=e.evaluator, evaluated_at=e.evaluated_at) for e in evals]


@router.post("/suppliers/{sid}/evaluations", response_model=EvaluationOut)
def create_evaluation(sid: int, data: EvaluationCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement", "quality_engineer"))):
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    if data.dimension not in VALID_DIMENSIONS:
        raise HTTPException(400, f"无效维度: {data.dimension}")
    ev = SupplierEvaluation(supplier_id=sid, dimension=data.dimension, score=data.score, weight=data.weight, comment=data.comment, evaluator=data.evaluator)
    db.add(ev)
    # 重算总分
    latest = {}
    for e in db.query(SupplierEvaluation).filter(SupplierEvaluation.supplier_id == sid).order_by(SupplierEvaluation.evaluated_at.desc()).all():
        if e.dimension not in latest: latest[e.dimension] = (e.score, e.weight)
    if latest:
        tw = sum(w for _, w in latest.values())
        s.overall_score = round(sum(s * w for s, w in latest.values()) / tw, 1) if tw > 0 else round(sum(s for s, _ in latest.values()) / len(latest), 1)
    db.commit(); db.refresh(ev)
    return EvaluationOut(id=ev.id, supplier_id=ev.supplier_id, dimension=ev.dimension, dimension_label=DIMENSION_LABELS.get(ev.dimension, ev.dimension), score=ev.score, weight=ev.weight, comment=ev.comment, evaluator=ev.evaluator, evaluated_at=ev.evaluated_at)


# ══════════════════════════════════════════════════
# 供应商聚合统计
# ══════════════════════════════════════════════════


@router.get("/suppliers/stats/summary", response_model=SupplierStatsOut)
def supplier_stats_summary(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    base = db.query(Supplier).filter(Supplier.is_deleted == 0)
    total = base.count()
    scores = [s.overall_score or 0 for s in base.all() if s.overall_score]
    cats = db.query(Supplier.category).filter(Supplier.is_deleted == 0, Supplier.category.isnot(None), Supplier.category != "").distinct().count()
    return SupplierStatsOut(total_count=total, qualified_count=base.filter(Supplier.status == "qualified").count(), active_count=base.filter(Supplier.status == "active").count(), suspended_count=base.filter(Supplier.status == "suspended").count(), blacklisted_count=base.filter(Supplier.status == "blacklisted").count(), avg_score=round(sum(scores)/len(scores), 1) if scores else 0, low_score_count=sum(1 for s in scores if s < 60), category_count=cats)


@router.get("/suppliers/ranking/list")
def supplier_ranking(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    suppliers = db.query(Supplier).filter(Supplier.is_deleted == 0).order_by(Supplier.overall_score.desc()).limit(limit).all()
    last_eval = dict(db.query(SupplierEvaluation.supplier_id, func.max(SupplierEvaluation.evaluated_at)).filter(SupplierEvaluation.supplier_id.in_([s.id for s in suppliers])).group_by(SupplierEvaluation.supplier_id).all())
    return [{"id": s.id, "name": s.name, "code": s.code, "category": s.category, "overall_score": s.overall_score or 0, "status": s.status, "evaluation_count": db.query(func.count(SupplierEvaluation.id)).filter(SupplierEvaluation.supplier_id == s.id).scalar() or 0, "last_evaluated": str(last_eval.get(s.id, "")) if last_eval.get(s.id) else None} for s in suppliers]


@router.get("/suppliers/categories/list")
def supplier_categories(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    rows = db.query(Supplier.category, func.count(Supplier.id).label("cnt")).filter(Supplier.is_deleted == 0, Supplier.category.isnot(None), Supplier.category != "").group_by(Supplier.category).order_by(func.count(Supplier.id).desc()).all()
    return [{"category": r.category, "count": r.cnt} for r in rows]
