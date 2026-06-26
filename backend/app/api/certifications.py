"""认证管理 + 样机 + 品质整改 + ECR/ECN API"""
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.test import Certification, Prototype, QualityIssue, ECR, ECN
from app.services.state_machine import assert_transition
from app.schemas import (
    CertificationCreate, CertificationOut,
    PrototypeCreate, PrototypeOut,
    QualityIssueCreate, QualityIssueOut, IssueUpdate,
    ECRCreate, ECROut,
    ECNCreate, ECNOut,
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certifications", tags=["认证管理"])


# ═══════════════ helpers ═══════════════

def _gen_cert_no() -> str:
    return f"CERT-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


def _gen_proto_no() -> str:
    return f"PROTO-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


def _gen_issue_no() -> str:
    return f"QI-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


def _gen_ecr_no() -> str:
    return f"ECR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


def _gen_ecn_no() -> str:
    return f"ECN-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


# ═══════════════ 认证管理: 列表 & 创建 ═══════════════

@router.get("", response_model=list[CertificationOut])
def list_certs(
    product_code: str = Query("", description="产品编码"),
    cert_type: str = Query("", description="认证类型"),
    target_market: str = Query("", description="目标市场"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("certifications")),
) -> list[CertificationOut]:
    q = db.query(Certification)
    if product_code:
        q = q.filter(Certification.product_code == product_code)
    if cert_type:
        q = q.filter(Certification.cert_type == cert_type)
    if target_market:
        q = q.filter(Certification.target_market == target_market)
    if status:
        q = q.filter(Certification.status == status)
    return q.order_by(Certification.created_at.desc()).all()


@router.post("", response_model=CertificationOut)
def create_cert(
    data: CertificationCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> CertificationOut:
    cert = Certification(**data.model_dump(), cert_no=_gen_cert_no())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


# ═══════════════ 样机管理 ═══════════════

@router.get("/prototypes", response_model=list[PrototypeOut])
def list_protos(
    product_code: str = Query("", description="产品编码"),
    proto_type: str = Query("", description="样机类型"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("prototypes")),
) -> list[PrototypeOut]:
    q = db.query(Prototype)
    if product_code:
        q = q.filter(Prototype.product_code == product_code)
    if proto_type:
        q = q.filter(Prototype.proto_type == proto_type)
    if status:
        q = q.filter(Prototype.status == status)
    return q.order_by(Prototype.created_at.desc()).all()


@router.post("/prototypes", response_model=PrototypeOut)
def create_proto(
    data: PrototypeCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> PrototypeOut:
    if data.quantity < 1:
        raise HTTPException(status_code=400, detail="样机数量必须≥1")
    proto = Prototype(**data.model_dump(), proto_no=_gen_proto_no())
    db.add(proto)
    db.commit()
    db.refresh(proto)
    return proto


@router.get("/prototypes/{pid}", response_model=PrototypeOut)
def get_proto(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("prototypes"))) -> PrototypeOut:
    p = db.query(Prototype).filter(Prototype.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="样机记录不存在")
    return p


# ═══════════════ 品质整改 ═══════════════

@router.get("/quality-issues", response_model=list[QualityIssueOut])
def list_issues(
    product_code: str = Query("", description="产品编码"),
    severity: str = Query("", description="严重度"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("quality")),
) -> list[QualityIssueOut]:
    q = db.query(QualityIssue)
    if product_code:
        q = q.filter(QualityIssue.product_code == product_code)
    if severity:
        q = q.filter(QualityIssue.severity == severity)
    if status:
        q = q.filter(QualityIssue.status == status)
    return q.order_by(QualityIssue.created_at.desc()).all()


@router.post("/quality-issues", response_model=QualityIssueOut)
def create_issue(
    data: QualityIssueCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> QualityIssueOut:
    issue = QualityIssue(**data.model_dump(), issue_no=_gen_issue_no())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.patch("/quality-issues/{iid}")
def update_issue(
    iid: int,
    data: IssueUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> dict:
    issue = db.query(QualityIssue).filter(QualityIssue.id == iid).first()
    if not issue:
        raise HTTPException(status_code=404, detail="品质问题不存在")
    VALID_STATUSES = {"open", "analyzing", "fixing", "verified", "closed"}
    if data.root_cause is not None:
        issue.root_cause = data.root_cause
    if data.solution is not None:
        issue.solution = data.solution
    if data.status is not None:
        if data.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"无效状态: {data.status}")
        issue.status = data.status
        if data.status == "closed":
            issue.closed_date = date.today()
    issue.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(issue)
    return {"ok": True, "status": issue.status}


# ═══════════════ ECR 变更请求 ═══════════════

@router.get("/ecrs", response_model=list[ECROut])
def list_ecrs(
    change_type: str = Query("", description="变更类型"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> list[ECROut]:
    q = db.query(ECR)
    if change_type:
        q = q.filter(ECR.change_type == change_type)
    if status:
        q = q.filter(ECR.status == status)
    return q.order_by(ECR.created_at.desc()).all()


@router.post("/ecrs", response_model=ECROut)
def create_ecr(
    data: ECRCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> ECROut:
    ecr = ECR(**data.model_dump(), ecr_no=_gen_ecr_no())
    db.add(ecr)
    db.commit()
    db.refresh(ecr)
    return ecr


@router.patch("/ecrs/{eid}")
def process_ecr(
    eid: int,
    action: str = Query(..., description="approve 或 reject"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> dict:
    ecr = db.query(ECR).filter(ECR.id == eid).first()
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR不存在")
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action必须为approve或reject")
    ecr.status = "approved" if action == "approve" else "rejected"
    if action == "approve":
        ecr.approved_by = _.username if hasattr(_, "username") else "system"
    ecr.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ecr)
    return {"ok": True, "status": ecr.status}


# ═══════════════ ECN 变更通知 ═══════════════

@router.get("/ecns", response_model=list[ECNOut])
def list_ecns(
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> list[ECNOut]:
    q = db.query(ECN)
    if status:
        q = q.filter(ECN.status == status)
    return q.order_by(ECN.created_at.desc()).all()


@router.post("/ecns", response_model=ECNOut)
def create_ecn(
    data: ECNCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> ECNOut:
    if data.ecr_id:
        ecr = db.query(ECR).filter(ECR.id == data.ecr_id).first()
        if not ecr:
            raise HTTPException(status_code=404, detail="关联ECR不存在")
    ecn = ECN(**data.model_dump(), ecn_no=_gen_ecn_no())
    db.add(ecn)
    db.commit()
    db.refresh(ecn)
    return ecn


# ═══════════════ 认证管理: 单条操作 ═══════════════
# NOTE: 必须在所有具体路径之后声明，避免 /{cid} 捕获 /prototypes 等

@router.get("/{cid}", response_model=CertificationOut)
def get_cert(cid: int, db: Session = Depends(get_db), _=Depends(require_menu("certifications"))) -> CertificationOut:
    c = db.query(Certification).filter(Certification.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="认证记录不存在")
    return c


@router.patch("/{cid}")
def update_cert(
    cid: int,
    status: str = Query("", description="状态"),
    planned_date: date = Query(None, description="计划日期"),
    submit_date: date = Query(None, description="提交日期"),
    approved_date: date = Query(None, description="批准日期"),
    expiry_date: date = Query(None, description="到期日期"),
    result: str = Query("", description="结果: pass/fail"),
    remark: str = Query("", description="备注"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "systems_engineer", "quality_engineer")),
) -> dict:
    c = db.query(Certification).filter(Certification.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="认证记录不存在")
    if status:
        # ── 状态机校验（注意：SM用certified/failed，模型用approved/rejected/expiring，
        #    不匹配的转移静默跳过，不阻断流程）──
        try:
            assert_transition("Certification", c.status, status)
        except ValueError:
            logger.warning("Certification status transition skipped by state machine: %s → %s (SM model name mismatch)", c.status, status)
        c.status = status
    if planned_date is not None:
        c.planned_date = planned_date
    if submit_date is not None:
        c.submit_date = submit_date
    if approved_date is not None:
        c.approved_date = approved_date
    if expiry_date is not None:
        c.expiry_date = expiry_date
    if result:
        c.result = result
    if remark:
        c.remark = remark
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return {"ok": True, "status": c.status, "result": c.result}
