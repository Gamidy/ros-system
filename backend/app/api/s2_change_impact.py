"""变更影响分析 API — Phase 6 S2

只读列表 + 详情
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_menu
from app.models.change_impact import ChangeImpactRecord
from app.schemas import ChangeImpactRecordOut

router = APIRouter(prefix="/api/s2/change-impact", tags=["S2-变更影响分析"])


@router.get("/records", response_model=list[ChangeImpactRecordOut])
def list_impact_records(
    prototype_id: int = Query(0, description="按样机筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-change-impact")),
) -> list:
    """变更影响分析记录列表"""
    q = db.query(ChangeImpactRecord)
    if prototype_id:
        q = q.filter(ChangeImpactRecord.prototype_id == prototype_id)
    return q.order_by(ChangeImpactRecord.created_at.desc()).all()


@router.get("/records/{record_id}", response_model=ChangeImpactRecordOut)
def get_impact_record(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-change-impact")),
) -> dict:
    """变更影响分析记录详情"""
    record = db.query(ChangeImpactRecord).filter(ChangeImpactRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="影响分析记录不存在")
    return record
