"""样机管理 API — Phase 6 S1"""
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.test import Prototype, TestResult
from app.schemas import (
    PrototypeCreate, PrototypeOut,
    TestResultOut,
)

router = APIRouter(prefix="/api/prototypes", tags=["样机管理"])


def _gen_proto_no() -> str:
    return f"PR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


@router.get("", response_model=list[PrototypeOut])
def list_prototypes(
    project_id: int = Query(None, description="项目ID"),
    version: str = Query("", description="版本"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
):
    q = db.query(Prototype)
    if project_id is not None:
        q = q.filter(Prototype.project_id == project_id)
    if version:
        q = q.filter(Prototype.version == version)
    if status:
        q = q.filter(Prototype.status == status)
    return q.order_by(Prototype.created_at.desc()).all()


@router.post("", response_model=PrototypeOut)
def create_prototype(
    data: PrototypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("prototypes")),
):
    proto = Prototype(
        **data.model_dump(),
        proto_no=_gen_proto_no(),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(proto)
    db.commit()
    db.refresh(proto)
    return proto


@router.get("/{pid}", response_model=PrototypeOut)
def get_prototype(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
):
    proto = db.query(Prototype).filter(Prototype.id == pid).first()
    if not proto:
        raise HTTPException(status_code=404, detail="样机不存在")
    return proto


@router.put("/{pid}", response_model=PrototypeOut)
def update_prototype(
    pid: int,
    data: PrototypeCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
):
    proto = db.query(Prototype).filter(Prototype.id == pid).first()
    if not proto:
        raise HTTPException(status_code=404, detail="样机不存在")
    for key, val in data.model_dump().items():
        setattr(proto, key, val)
    proto.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proto)
    return proto


@router.patch("/{pid}/status")
def patch_prototype_status(
    pid: int,
    status: str = Query(..., description="目标状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
):
    proto = db.query(Prototype).filter(Prototype.id == pid).first()
    if not proto:
        raise HTTPException(status_code=404, detail="样机不存在")
    proto.status = status
    proto.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": proto.status}


@router.get("/{pid}/judgments", response_model=list[TestResultOut])
def get_prototype_judgments(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
):
    """该样机的所有 TestResult（判定）"""
    proto = db.query(Prototype).filter(Prototype.id == pid).first()
    if not proto:
        raise HTTPException(status_code=404, detail="样机不存在")
    results = db.query(TestResult).filter(TestResult.prototype_id == pid).all()
    return results


@router.post("/{pid}/upgrade")
def upgrade_prototype(
    pid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("prototypes")),
):
    """版本升级：归档旧判定，创建新版"""
    proto = db.query(Prototype).filter(Prototype.id == pid).first()
    if not proto:
        raise HTTPException(status_code=404, detail="样机不存在")

    # 归档旧判定（将旧 TestResult 的 prototype_id 置为 None）
    db.query(TestResult).filter(TestResult.prototype_id == pid).update(
        {"prototype_id": None}
    )

    # 创建新版样机（继承大部分字段）
    new_version = str(int(proto.version or "1") + 1) if proto.version else "2"
    new_proto = Prototype(
        proto_no=_gen_proto_no(),
        product_code=proto.product_code,
        project_code=proto.project_code,
        proto_type=proto.proto_type,
        version=new_version,
        project_id=proto.project_id,
        parent_prototype_id=pid,
        bom_version=proto.bom_version,
        firmware_version=proto.firmware_version,
        stage=proto.stage,
        quantity=proto.quantity,
        status="producing",
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(new_proto)
    db.commit()
    db.refresh(new_proto)
    return {
        "ok": True,
        "old_prototype_id": pid,
        "new_prototype_id": new_proto.id,
        "new_version": new_version,
        "message": "旧判定已归档，新版样机已创建",
    }
