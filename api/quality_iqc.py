"""来料检验(IQC) API"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.quality_iqc import IQCRecord, IQCItem

router = APIRouter(prefix="/quality/iqc", tags=["来料检验"])


def _record_out(r: IQCRecord) -> dict:
    return {
        "id": r.id, "receipt_no": r.receipt_no, "supplier": r.supplier,
        "part_code": r.part_code, "part_name": r.part_name, "batch_no": r.batch_no,
        "quantity": r.quantity, "sample_qty": r.sample_qty,
        "accept_qty": r.accept_qty, "reject_qty": r.reject_qty,
        "aql": r.aql, "inspection_level": r.inspection_level,
        "verdict": r.verdict, "inspector": r.inspector,
        "inspect_date": str(r.inspect_date) if r.inspect_date else None,
        "remark": r.remark,
        "created_at": str(r.created_at) if r.created_at else None,
        "defect_rate": round(r.reject_qty / r.sample_qty * 100, 1) if r.sample_qty > 0 else 0,
    }


@router.get("")
def list_iqc(
    supplier: str | None = None,
    part_code: str | None = None,
    verdict: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(IQCRecord)
    if supplier: q = q.filter(IQCRecord.supplier.ilike(f"%{supplier}%"))
    if part_code: q = q.filter(IQCRecord.part_code.ilike(f"%{part_code}%"))
    if verdict: q = q.filter(IQCRecord.verdict == verdict)
    if date_from: q = q.filter(IQCRecord.inspect_date >= date.fromisoformat(date_from))
    if date_to: q = q.filter(IQCRecord.inspect_date <= date.fromisoformat(date_to))
    return [_record_out(r) for r in q.order_by(IQCRecord.id.desc()).limit(100).all()]


@router.get("/{rid}")
def get_iqc(rid: int, db: Session = Depends(get_db)):
    r = db.query(IQCRecord).filter(IQCRecord.id == rid).first()
    if not r: raise HTTPException(404, "记录不存在")
    result = _record_out(r)
    result["items"] = [{
        "id": i.id, "item_name": i.item_name, "spec": i.spec,
        "measured": i.measured, "result": i.result,
    } for i in db.query(IQCItem).filter(IQCItem.record_id == rid).all()]
    return result


@router.post("")
def create_iqc(data: dict, db: Session = Depends(get_db)):
    valid_fields = {c.name for c in IQCRecord.__table__.columns}
    r = IQCRecord(**{k: v for k, v in data.items() if k in valid_fields})
    db.add(r); db.flush()
    for item in data.get("items", []):
        db.add(IQCItem(record_id=r.id, **item))
    db.commit(); db.refresh(r)
    return _record_out(r)


@router.put("/{rid}")
def update_iqc(rid: int, data: dict, db: Session = Depends(get_db)):
    r = db.query(IQCRecord).filter(IQCRecord.id == rid).first()
    if not r: raise HTTPException(404, "记录不存在")
    for k, v in data.items():
        if k != "items" and hasattr(r, k): setattr(r, k, v)
    db.flush()
    if "items" in data:
        db.query(IQCItem).filter(IQCItem.record_id == rid).delete()
        for item in data["items"]:
            db.add(IQCItem(record_id=rid, **item))
    db.commit(); db.refresh(r)
    return _record_out(r)


@router.delete("/{rid}")
def delete_iqc(rid: int, db: Session = Depends(get_db)):
    r = db.query(IQCRecord).filter(IQCRecord.id == rid).first()
    if not r: raise HTTPException(404, "记录不存在")
    db.delete(r); db.commit()
    return {"message": "已删除"}
