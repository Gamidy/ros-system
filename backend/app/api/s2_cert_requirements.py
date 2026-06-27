"""认证需求 API — Phase 6 S2

只读列表 + 详情 + 触发自动生成（调用 CertAutoGenService）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.certification import CertificationRequirement
from app.schemas import CertificationRequirementOut
from app.services.cert_auto_gen import CertAutoGenService
from app.services.event_bus import emit as d2_emit

router = APIRouter(prefix="/api/s2/certification-requirements", tags=["S2-认证需求"])


@router.get("", response_model=list[CertificationRequirementOut])
def list_cert_requirements(
    project_id: int = Query(0, description="按项目筛选"),
    cert_type: str = Query("", description="按认证类型筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-requirements")),
) -> list[CertificationRequirementOut]:
    """认证需求列表（只读）"""
    q = db.query(CertificationRequirement)
    if project_id:
        q = q.filter(CertificationRequirement.project_id == project_id)
    if cert_type:
        q = q.filter(CertificationRequirement.cert_type == cert_type)
    return q.order_by(CertificationRequirement.created_at.desc()).all()


@router.get("/{req_id}", response_model=CertificationRequirementOut)
def get_cert_requirement(
    req_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-requirements")),
) -> CertificationRequirementOut:
    """认证需求详情"""
    req = db.query(CertificationRequirement).filter(CertificationRequirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="认证需求不存在")
    return req


@router.post("/generate")
def generate_cert_requirements(
    project_id: int = Query(..., description="项目ID"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-requirements")),
) -> dict:
    """触发自动生成认证需求（调用 CertAutoGenService）"""
    service = CertAutoGenService(db)
    result = service.generate_from_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "生成失败"))
    try:
        d2_emit('cert.requirement.created', {
            'requirement_id': result.get('requirement_id'),
            'project_id': project_id,
            'target_market_id': result.get('target_market_id'),
            'cert_type': result.get('cert_type'),
            'created_by': getattr(_, 'id', None),
        })
    except Exception:
        pass
    return result
