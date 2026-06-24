"""认证样机 API — Phase 6 S2

标准 CRUD，创建时校验 prototype_id 必须存在
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.certification import CertificationSample
from app.models.test import Prototype
from app.schemas import CertificationSampleCreate, CertificationSampleUpdate, CertificationSampleOut
from datetime import date
from uuid import uuid4

router = APIRouter(prefix="/api/s2/certification-samples", tags=["S2-认证样机"])


def _gen_sample_no() -> str:
    return f"CS-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


@router.get("", response_model=list[CertificationSampleOut])
def list_cert_samples(
    cert_project_id: int = Query(0, description="按认证项目筛选"),
    prototype_id: int = Query(0, description="按原型筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("certifications")),
):
    """认证样机列表"""
    q = db.query(CertificationSample)
    if cert_project_id:
        q = q.filter(CertificationSample.cert_project_id == cert_project_id)
    if prototype_id:
        q = q.filter(CertificationSample.prototype_id == prototype_id)
    return q.order_by(CertificationSample.created_at.desc()).all()


@router.post("", response_model=CertificationSampleOut, status_code=201)
def create_cert_sample(
    data: CertificationSampleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("certifications")),
):
    """创建认证样机（校验 prototype_id 必须存在）"""
    prototype = db.query(Prototype).filter(Prototype.id == data.prototype_id).first()
    if not prototype:
        raise HTTPException(status_code=400, detail=f"样机(Prototype) {data.prototype_id} 不存在")

    if not data.sample_no:
        data.sample_no = _gen_sample_no()
    sample = CertificationSample(
        **data.model_dump(exclude_unset=True),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


@router.put("/{cs_id}", response_model=CertificationSampleOut)
def update_cert_sample(
    cs_id: int,
    data: CertificationSampleUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("certifications")),
):
    """更新认证样机"""
    sample = db.query(CertificationSample).filter(CertificationSample.id == cs_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="认证样机不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(sample, key, val)
    db.commit()
    db.refresh(sample)
    return sample
