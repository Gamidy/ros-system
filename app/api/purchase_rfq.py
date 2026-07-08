"""询比价管理(RFQ) API"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.purchase_rfq import RFQ, RFQQuotation

router = APIRouter(prefix="/purchase/rfqs", tags=["询比价管理"])


def _rfq_out(r: RFQ) -> dict:
    return {
        "id": r.id, "rfq_no": r.rfq_no, "title": r.title,
        "items": r.items, "suppliers": r.suppliers,
        "deadline": str(r.deadline) if r.deadline else None,
        "status": r.status, "created_by": r.created_by,
        "remark": r.remark,
        "created_at": str(r.created_at) if r.created_at else None,
    }


@router.get("")
def list_rfq(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(RFQ)
    if status: q = q.filter(RFQ.status == status)
    return [_rfq_out(r) for r in q.order_by(RFQ.id.desc()).limit(50).all()]


@router.get("/{rid}")
def get_rfq(rid: int, db: Session = Depends(get_db)):
    r = db.query(RFQ).filter(RFQ.id == rid).first()
    if not r: raise HTTPException(404, "询价单不存在")
    result = _rfq_out(r)
    result["quotations"] = [{
        "id": q.id, "supplier_name": q.supplier_name,
        "items": q.items, "total_amount": q.total_amount,
        "delivery_days": q.delivery_days, "payment_terms": q.payment_terms,
        "valid_until": str(q.valid_until) if q.valid_until else None,
        "contact": q.contact, "remark": q.remark,
        "created_at": str(q.created_at) if q.created_at else None,
    } for q in db.query(RFQQuotation).filter(RFQQuotation.rfq_id == rid).all()]
    # 比价表: 最低价/最高价/平均价
    prices = [q.total_amount for q in db.query(RFQQuotation).filter(RFQQuotation.rfq_id == rid).all() if q.total_amount]
    result["price_analysis"] = {
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "avg": round(sum(prices) / len(prices), 2) if prices else 0,
        "quotation_count": len(prices),
    } if prices else None
    return result


@router.post("")
def create_rfq(data: dict, db: Session = Depends(get_db)):
    from datetime import datetime
    r = RFQ(**{k: v for k, v in data.items() if k in ["title", "items", "suppliers", "deadline", "remark"]})
    r.rfq_no = f"RFQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    r.status = "draft"
    db.add(r); db.commit(); db.refresh(r)
    return _rfq_out(r)


@router.put("/{rid}")
def update_rfq(rid: int, data: dict, db: Session = Depends(get_db)):
    r = db.query(RFQ).filter(RFQ.id == rid).first()
    if not r: raise HTTPException(404, "询价单不存在")
    for k, v in data.items():
        if hasattr(r, k): setattr(r, k, v)
    db.commit(); db.refresh(r)
    return _rfq_out(r)


@router.delete("/{rid}")
def delete_rfq(rid: int, db: Session = Depends(get_db)):
    r = db.query(RFQ).filter(RFQ.id == rid).first()
    if not r: raise HTTPException(404, "询价单不存在")
    db.delete(r); db.commit()
    return {"message": "已删除"}


# ═══ 报价管理 ═══

@router.post("/{rid}/quotations")
def create_quotation(rid: int, data: dict, db: Session = Depends(get_db)):
    r = db.query(RFQ).filter(RFQ.id == rid).first()
    if not r: raise HTTPException(404, "询价单不存在")
    q = RFQQuotation(rfq_id=rid, **{k: v for k, v in data.items()})
    db.add(q)
    r.status = "quoting"
    db.commit(); db.refresh(q)
    return {"id": q.id, "supplier_name": q.supplier_name, "total_amount": q.total_amount}


@router.delete("/{rid}/quotations/{qid}")
def delete_quotation(rid: int, qid: int, db: Session = Depends(get_db)):
    q = db.query(RFQQuotation).filter(RFQQuotation.id == qid, RFQQuotation.rfq_id == rid).first()
    if not q: raise HTTPException(404, "报价不存在")
    db.delete(q); db.commit()
    return {"message": "已删除"}
