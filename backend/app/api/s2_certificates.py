"""证书管理 API — Phase 6 S2

标准 CRUD + 续证/暂停/注销 + 快到期列表
"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.certification import Certificate, CertificateVersion
from pydantic import BaseModel

from app.schemas import CertificateCreate, CertificateUpdate, CertificateOut, CertificateVersionCreate, CertificateVersionOut
from app.services.event_bus import emit as d2_emit


class ActionResponse(BaseModel):
    """简单操作响应"""
    success: bool
    message: str = ""

router = APIRouter(prefix="/api/s2/certificates", tags=["S2-证书管理"])


@router.get("", response_model=list[CertificateOut])
def list_certificates(
    cert_type: str = Query("", description="按认证类型筛选"),
    status: str = Query("", description="按状态筛选"),
    cert_no: str = Query("", description="按证书编号搜索"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("certificates")),
) -> list[CertificateOut]:
    """证书列表"""
    q = db.query(Certificate)
    if cert_type:
        q = q.filter(Certificate.cert_type == cert_type)
    if status:
        q = q.filter(Certificate.status == status)
    if cert_no:
        q = q.filter(Certificate.cert_no.ilike(f"%{cert_no}%"))
    return q.order_by(Certificate.created_at.desc()).all()


@router.get("/expiring", response_model=list[CertificateOut])
def list_expiring_certificates(
    days: int = Query(30, description="到期天数范围"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("certificates")),
) -> list[CertificateOut]:
    """快到期证书列表（默认30天内）"""
    today = date.today()
    deadline = today + timedelta(days=days)
    q = db.query(Certificate).filter(
        and_(
            Certificate.expiry_date >= today,
            Certificate.expiry_date <= deadline,
            Certificate.status == "active",
        )
    )
    return q.order_by(Certificate.expiry_date).all()


@router.post("", response_model=CertificateOut, status_code=201)
def create_certificate(
    data: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("certificates")),
) -> CertificateOut:
    """创建证书"""
    cert = Certificate(
        **data.model_dump(exclude_unset=True),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    try:
        d2_emit('cert.certificate.issued', {
            'cert_id': cert.id,
            'cert_no': cert.cert_no,
            'cert_type': cert.cert_type,
            'issue_date': str(cert.issue_date) if cert.issue_date else None,
            'expiry_date': str(cert.expiry_date) if cert.expiry_date else None,
            'certified_body': getattr(cert, 'issuing_body', None),
        })
    except Exception:
        pass
    return cert


@router.put("/{cert_id}", response_model=CertificateOut)
def update_certificate(
    cert_id: int,
    data: CertificateUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("certificates")),
) -> CertificateOut:
    """更新证书"""
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="证书不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(cert, key, val)
    db.commit()
    db.refresh(cert)
    return cert


@router.post("/{cert_id}/renew", response_model=CertificateVersionOut)
def renew_certificate(
    cert_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _=Depends(require_menu("certificates")),
) -> CertificateVersionOut:
    """续证 — 创建新版本

    原证书标记为过期，创建新版本记录
    """
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="证书不存在")

    # 计算新版本号
    existing_versions = db.query(CertificateVersion).filter(
        CertificateVersion.certificate_id == cert_id
    ).count()
    new_version_no = f"V{existing_versions + 1}"

    # 创建新版本
    version = CertificateVersion(
        certificate_id=cert_id,
        version_no=new_version_no,
        cert_no=data.get("cert_no", cert.cert_no),
        issuing_body=data.get("issuing_body", cert.issuing_body),
        issue_date=data.get("issue_date", date.today()),
        expiry_date=data.get("expiry_date"),
        status="active",
        change_reason=data.get("change_reason", "续证"),
        org_id=getattr(cert, "org_id", None),
    )
    db.add(version)

    # 更新原证书信息
    if "cert_no" in data:
        cert.cert_no = data["cert_no"]
    if "expiry_date" in data:
        cert.expiry_date = data["expiry_date"]
    if "issue_date" in data:
        cert.issue_date = data["issue_date"]
    cert.status = "active"

    db.commit()
    db.refresh(version)
    return version


@router.post("/{cert_id}/suspend")
def suspend_certificate(
    cert_id: int,
    data: dict = {},
    db: Session = Depends(get_db),
    _=Depends(require_menu("certificates")),
) -> ActionResponse:
    """暂停证书"""
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="证书不存在")
    if cert.status != "active":
        raise HTTPException(status_code=400, detail=f"当前状态 '{cert.status}' 不允许暂停")
    cert.status = "suspended"
    db.commit()
    return {"success": True, "message": f"证书 {cert.cert_no} 已暂停"}


@router.post("/{cert_id}/revoke")
def revoke_certificate(
    cert_id: int,
    data: dict = {},
    db: Session = Depends(get_db),
    _=Depends(require_menu("certificates")),
) -> ActionResponse:
    """注销证书"""
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="证书不存在")
    if cert.status == "revoked":
        raise HTTPException(status_code=400, detail="证书已注销")
    cert.status = "revoked"
    db.commit()
    return {"success": True, "message": f"证书 {cert.cert_no} 已注销"}
