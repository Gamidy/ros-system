"""验证需求 API — Phase 6 S1"""
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.verification_requirement import VerificationRequirement
from app.schemas import (
    VerificationRequirementCreate, VerificationRequirementOut,
    VerificationRequirementGenerateRequest,
)

router = APIRouter(prefix="/api/verification-requirements", tags=["验证需求"])


def _gen_vr_code() -> str:
    return f"VR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


@router.get("", response_model=list[VerificationRequirementOut])
def list_verification_requirements(
    category: str = Query("", description="分类"),
    source_type: str = Query("", description="来源类型"),
    status: str = Query("", description="状态"),
    project_id: int = Query(None, description="项目ID"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("verification-requirements")),
) -> list:
    q = db.query(VerificationRequirement)
    if category:
        q = q.filter(VerificationRequirement.category == category)
    if source_type:
        q = q.filter(VerificationRequirement.source_type == source_type)
    if status:
        q = q.filter(VerificationRequirement.status == status)
    if project_id is not None:
        q = q.filter(VerificationRequirement.project_id == project_id)
    return q.order_by(VerificationRequirement.created_at.desc()).all()


@router.post("", response_model=VerificationRequirementOut)
def create_verification_requirement(
    data: VerificationRequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("verification-requirements")),
) -> dict:
    vr = VerificationRequirement(
        **data.model_dump(),
        vr_code=_gen_vr_code(),
        status="pending",
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(vr)
    db.commit()
    db.refresh(vr)
    return vr


@router.get("/{rid}", response_model=VerificationRequirementOut)
def get_verification_requirement(
    rid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("verification-requirements")),
) -> dict:
    vr = db.query(VerificationRequirement).filter(VerificationRequirement.id == rid).first()
    if not vr:
        raise HTTPException(status_code=404, detail="验证需求不存在")
    return vr


@router.put("/{rid}", response_model=VerificationRequirementOut)
def update_verification_requirement(
    rid: int,
    data: VerificationRequirementCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("verification-requirements")),
) -> dict:
    vr = db.query(VerificationRequirement).filter(VerificationRequirement.id == rid).first()
    if not vr:
        raise HTTPException(status_code=404, detail="验证需求不存在")
    for key, val in data.model_dump().items():
        setattr(vr, key, val)
    vr.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vr)
    return vr


@router.patch("/{rid}/status")
def patch_vr_status(
    rid: int,
    status: str = Query(..., description="目标状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("verification-requirements")),
) -> dict:
    vr = db.query(VerificationRequirement).filter(VerificationRequirement.id == rid).first()
    if not vr:
        raise HTTPException(status_code=404, detail="验证需求不存在")
    vr.status = status
    vr.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": vr.status}


@router.post("/generate-from-plan")
def generate_vr_from_plan(
    data: VerificationRequirementGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("verification-requirements")),
) -> dict:
    """从 ProductPlan 自动生成 VR（骨架实现）"""
    from app.models.product_plan import ProductPlan

    plan = db.query(ProductPlan).filter(ProductPlan.id == data.product_plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="产品策划不存在")

    # 骨架实现: 创建一条示例 VR
    vr = VerificationRequirement(
        vr_code=_gen_vr_code(),
        title=f"从策划自动生成: {plan.name}",
        category="performance",
        source_type="product_plan",
        source_id=str(plan.id),
        product_plan_id=plan.id if isinstance(plan.id, int) else None,
        status="pending",
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(vr)
    db.commit()
    db.refresh(vr)
    return {"ok": True, "vr_id": vr.id, "vr_code": vr.vr_code}
