"""客户投诉管理API"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.quality_complaint import CustomerComplaint

router = APIRouter(prefix="/quality/complaints", tags=["客户投诉管理"])


@router.get("")
def list_complaints(
    status: str | None = None,
    severity: str | None = None,
    customer: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(CustomerComplaint)
    if status: q = q.filter(CustomerComplaint.status == status)
    if severity: q = q.filter(CustomerComplaint.severity == severity)
    if customer: q = q.filter(CustomerComplaint.customer_name.ilike(f"%{customer}%"))
    records = q.order_by(CustomerComplaint.id.desc()).limit(100).all()
    return [{
        "id": r.id, "complaint_no": r.complaint_no, "customer_name": r.customer_name,
        "product_code": r.product_code, "complaint_type": r.complaint_type,
        "severity": r.severity, "title": r.title, "status": r.status,
        "handler": r.handler, "complain_date": str(r.complain_date) if r.complain_date else None,
        "closed_date": str(r.closed_date) if r.closed_date else None,
    } for r in records]


@router.get("/{cid}")
def get_complaint(cid: int, db: Session = Depends(get_db)):
    r = db.query(CustomerComplaint).filter(CustomerComplaint.id == cid).first()
    if not r: raise HTTPException(404, "投诉不存在")
    return {
        "id": r.id, "complaint_no": r.complaint_no, "customer_name": r.customer_name,
        "product_code": r.product_code, "batch_no": r.batch_no, "qty_involved": r.qty_involved,
        "complaint_type": r.complaint_type, "severity": r.severity,
        "title": r.title, "description": r.description,
        "root_cause": r.root_cause, "corrective_action": r.corrective_action,
        "preventive_action": r.preventive_action,
        "status": r.status, "handler": r.handler,
        "complain_date": str(r.complain_date) if r.complain_date else None,
        "closed_date": str(r.closed_date) if r.closed_date else None,
        "remark": r.remark,
        "created_at": str(r.created_at) if r.created_at else None,
    }


@router.post("")
def create_complaint(data: dict, db: Session = Depends(get_db)):
    from datetime import datetime
    valid_fields = {c.name for c in CustomerComplaint.__table__.columns}
    r = CustomerComplaint(**{k: v for k, v in data.items() if k in valid_fields})
    r.complaint_no = f"COMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    r.status = "open"
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "complaint_no": r.complaint_no}


@router.put("/{cid}")
def update_complaint(cid: int, data: dict, db: Session = Depends(get_db)):
    r = db.query(CustomerComplaint).filter(CustomerComplaint.id == cid).first()
    if not r: raise HTTPException(404, "投诉不存在")
    for k, v in data.items():
        if hasattr(r, k): setattr(r, k, v)
    db.commit(); db.refresh(r)
    return {"message": "已更新"}
