"""认证项目 API — Phase 6 S2

标准 CRUD + 状态流转
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.certification import CertificationProject
from app.schemas import CertificationProjectCreate, CertificationProjectUpdate, CertificationProjectOut
from datetime import date, datetime
from uuid import uuid4

router = APIRouter(prefix="/api/s2/certification-projects", tags=["S2-认证项目"])


def _gen_cert_project_code() -> str:
    return f"CP-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


@router.get("", response_model=list[CertificationProjectOut])
def list_cert_projects(
    project_id: int = Query(0, description="按项目筛选"),
    status: str = Query("", description="按状态筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-projects")),
) -> list[CertificationProjectOut]:
    """认证项目列表"""
    q = db.query(CertificationProject)
    if project_id:
        q = q.filter(CertificationProject.project_id == project_id)
    if status:
        q = q.filter(CertificationProject.status == status)
    return q.order_by(CertificationProject.created_at.desc()).all()


@router.post("", response_model=CertificationProjectOut, status_code=201)
def create_cert_project(
    data: CertificationProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("cert-projects")),
) -> CertificationProjectOut:
    """创建认证项目"""
    if not data.code:
        data.code = _gen_cert_project_code()
    project = CertificationProject(
        **data.model_dump(exclude_unset=True),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{cp_id}", response_model=CertificationProjectOut)
def get_cert_project(
    cp_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-projects")),
) -> CertificationProjectOut:
    """认证项目详情"""
    project = db.query(CertificationProject).filter(CertificationProject.id == cp_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="认证项目不存在")
    return project


@router.put("/{cp_id}", response_model=CertificationProjectOut)
def update_cert_project(
    cp_id: int,
    data: CertificationProjectUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-projects")),
) -> CertificationProjectOut:
    """更新认证项目"""
    project = db.query(CertificationProject).filter(CertificationProject.id == cp_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="认证项目不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(project, key, val)
    db.commit()
    db.refresh(project)
    return project


class StatusUpdateRequest:
    status: str


@router.patch("/{cp_id}/status", response_model=CertificationProjectOut)
def update_cert_project_status(
    cp_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-projects")),
) -> dict:
    """认证项目状态流转"""
    project = db.query(CertificationProject).filter(CertificationProject.id == cp_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="认证项目不存在")
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status 字段必填")
    project.status = new_status
    db.commit()
    db.refresh(project)
    return project
