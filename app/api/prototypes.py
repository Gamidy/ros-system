"""样机管理 API — Phase 6 S1"""
from datetime import date, datetime, timezone
from uuid import uuid4
import logging

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prototypes", tags=["样机管理"])


def _gen_proto_no() -> str:
    return f"PR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


@router.get("", response_model=list[PrototypeOut])
def list_prototypes(
    project_id: int = Query(None, description="项目ID"),
    version: str = Query("", description="版本"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
) -> list[PrototypeOut]:
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
) -> PrototypeOut:
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
) -> PrototypeOut:
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
) -> PrototypeOut:
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
) -> dict:
    proto = db.query(Prototype).filter(Prototype.id == pid).first()
    if not proto:
        raise HTTPException(status_code=404, detail="样机不存在")
    old_status = proto.status
    proto.status = status
    proto.updated_at = datetime.now(timezone.utc)
    db.flush()

    # 当 Prototype 状态变为 done 且 version=P2 时，自动创建 CertificationSample
    if status == "done" and proto.version == "P2" and old_status != "done":
        try:
            from app.models.certification import CertificationProject, CertificationSample
            from app.core.enums_s2 import CertSampleStatus
            from uuid import uuid4

            # 查找该 prototype 所属项目下的认证项目
            cert_projects = db.query(CertificationProject).filter(
                CertificationProject.project_id == proto.project_id
            ).all()
            for cp in cert_projects:
                # 检查是否已存在关联的认证样机
                existing = db.query(CertificationSample).filter(
                    CertificationSample.prototype_id == pid,
                    CertificationSample.cert_project_id == cp.id,
                ).first()
                if existing:
                    continue
                sample = CertificationSample(
                    cert_project_id=cp.id,
                    prototype_id=pid,
                    cert_type="CE",  # 默认认证类型，后续可由用户编辑
                    sample_no=f"CS-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}",
                    status=CertSampleStatus.PENDING.value,
                    org_id=getattr(proto, "org_id", None),
                )
                db.add(sample)
        except Exception as e:
            logger.warning(f"自动创建认证样机失败: {e}")
            pass  # 自动创建认证样机是辅助功能，不应阻塞状态更新

    db.commit()
    return {"ok": True, "status": proto.status}


@router.get("/{pid}/judgments", response_model=list[TestResultOut])
def get_prototype_judgments(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
) -> list[TestResultOut]:
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
) -> dict:
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
