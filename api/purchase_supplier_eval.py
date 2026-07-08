"""供应商评估API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.purchase_supplier_eval import SupplierEvaluation

router = APIRouter(prefix="/purchase/supplier-evaluations", tags=["供应商评估"])


@router.get("")
def list_evaluations(supplier: str | None = None, db: Session = Depends(get_db)):
    q = db.query(SupplierEvaluation)
    if supplier: q = q.filter(SupplierEvaluation.supplier_name.ilike(f"%{supplier}%"))
    records = q.order_by(SupplierEvaluation.id.desc()).limit(100).all()
    return [{
        "id": r.id, "supplier_name": r.supplier_name, "eval_period": r.eval_period,
        "eval_date": str(r.eval_date) if r.eval_date else None,
        "quality_score": r.quality_score, "delivery_score": r.delivery_score,
        "price_score": r.price_score, "service_score": r.service_score,
        "total_score": r.total_score, "grade": r.grade,
        "evaluator": r.evaluator,
    } for r in records]


@router.post("")
def create_evaluation(data: dict, db: Session = Depends(get_db)):
    r = SupplierEvaluation(**{k: v for k, v in data.items() if k not in ["id"]})
    # 自动计算综合得分 (质量40% 交付25% 价格20% 服务15%)，缺省为0
    qs = r.quality_score or 0; ds = r.delivery_score or 0
    ps = r.price_score or 0; ss = r.service_score or 0
    r.total_score = round(qs * 0.4 + ds * 0.25 + ps * 0.2 + ss * 0.15, 1)
    # 自动评等级
    r.grade = "A" if r.total_score >= 90 else "B" if r.total_score >= 75 else "C" if r.total_score >= 60 else "D"
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "total_score": r.total_score, "grade": r.grade}


@router.put("/{eid}")
def update_evaluation(eid: int, data: dict, db: Session = Depends(get_db)):
    r = db.query(SupplierEvaluation).filter(SupplierEvaluation.id == eid).first()
    if not r: raise HTTPException(404, "评估不存在")
    for k, v in data.items():
        if hasattr(r, k): setattr(r, k, v)
    qs = r.quality_score or 0; ds = r.delivery_score or 0
    ps = r.price_score or 0; ss = r.service_score or 0
    r.total_score = round(qs * 0.4 + ds * 0.25 + ps * 0.2 + ss * 0.15, 1)
    r.grade = "A" if r.total_score >= 90 else "B" if r.total_score >= 75 else "C" if r.total_score >= 60 else "D"
    db.commit(); db.refresh(r)
    return {"id": r.id, "total_score": r.total_score, "grade": r.grade}


@router.delete("/{eid}")
def delete_evaluation(eid: int, db: Session = Depends(get_db)):
    r = db.query(SupplierEvaluation).filter(SupplierEvaluation.id == eid).first()
    if not r: raise HTTPException(404, "评估不存在")
    db.delete(r); db.commit()
    return {"message": "已删除"}
