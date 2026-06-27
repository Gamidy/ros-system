"""认证结果 API — Phase 6 S2

GET/POST/PATCH 标准 + 状态流转
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.certification import CertificationResult
from app.schemas import CertificationResultCreate, CertificationResultUpdate, CertificationResultOut

router = APIRouter(prefix="/api/s2/certification-results", tags=["S2-认证结果"])


@router.get("", response_model=list[CertificationResultOut])
def list_cert_results(
    cert_execution_id: int = Query(0, description="按认证执行筛选"),
    status: str = Query("", description="按状态筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-results")),
) -> list[CertificationResultOut]:
    """认证结果列表"""
    q = db.query(CertificationResult)
    if cert_execution_id:
        q = q.filter(CertificationResult.cert_execution_id == cert_execution_id)
    if status:
        q = q.filter(CertificationResult.status == status)
    return q.order_by(CertificationResult.created_at.desc()).all()


@router.post("", response_model=CertificationResultOut, status_code=201)
def create_cert_result(
    data: CertificationResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("cert-results")),
) -> CertificationResultOut:
    """创建认证结果"""
    result = CertificationResult(
        **data.model_dump(exclude_unset=True),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.patch("/{cr_id}", response_model=CertificationResultOut)
def update_cert_result(
    cr_id: int,
    data: CertificationResultUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-results")),
) -> CertificationResultOut:
    """更新认证结果"""
    result = db.query(CertificationResult).filter(CertificationResult.id == cr_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="认证结果不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(result, key, val)
    db.commit()
    db.refresh(result)
    return result


@router.patch("/{cr_id}/status", response_model=CertificationResultOut)
def update_cert_result_status(
    cr_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-results")),
) -> CertificationResultOut:
    """认证结果状态流转"""
    result = db.query(CertificationResult).filter(CertificationResult.id == cr_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="认证结果不存在")
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status 字段必填")
    result.status = new_status
    db.commit()
    db.refresh(result)
    return result
