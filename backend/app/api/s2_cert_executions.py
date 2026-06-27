"""认证执行 API — Phase 6 S2

GET/POST/PATCH 标准
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.certification import CertificationExecution
from app.schemas import CertificationExecutionCreate, CertificationExecutionUpdate, CertificationExecutionOut
from app.services.event_bus import emit as d2_emit

router = APIRouter(prefix="/api/s2/certification-executions", tags=["S2-认证执行"])


@router.get("", response_model=list[CertificationExecutionOut])
def list_cert_executions(
    cert_sample_id: int = Query(0, description="按认证样机筛选"),
    status: str = Query("", description="按状态筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-executions")),
) -> list[CertificationExecutionOut]:
    """认证执行列表"""
    q = db.query(CertificationExecution)
    if cert_sample_id:
        q = q.filter(CertificationExecution.cert_sample_id == cert_sample_id)
    if status:
        q = q.filter(CertificationExecution.status == status)
    return q.order_by(CertificationExecution.created_at.desc()).all()


@router.post("", response_model=CertificationExecutionOut, status_code=201)
def create_cert_execution(
    data: CertificationExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("cert-executions")),
) -> CertificationExecutionOut:
    """创建认证执行"""
    execution = CertificationExecution(
        **data.model_dump(exclude_unset=True),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


@router.patch("/{ce_id}", response_model=CertificationExecutionOut)
def update_cert_execution(
    ce_id: int,
    data: CertificationExecutionUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-executions")),
) -> CertificationExecutionOut:
    """更新认证执行"""
    execution = db.query(CertificationExecution).filter(CertificationExecution.id == ce_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="认证执行不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(execution, key, val)
    db.commit()
    db.refresh(execution)
    try:
        if execution.status in ('passed', 'failed'):
            d2_emit('cert.execution.completed', {
                'execution_id': execution.id,
                'cert_project_id': execution.cert_project_id,
                'status': execution.status,
                'completed_at': str(getattr(execution, 'updated_at', None) or execution.created_at),
            })
    except Exception:
        pass
    return execution
