"""Phase 6 S3 — ECR (Engineering Change Request) 工程变更申请 API
（审批工作流拆分到 ecr_workflow.py，附件管理拆分到 ecr_attachments.py）"""
import json
import os
import shutil
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.enums import ECRStatus, ECRType, ECRUrgency, ECOStatus
from app.core.permissions import require_menu
from app.core.security import get_current_user
from app.models.approval import ApprovalRequest
from app.models.ci_v2_impact import ImpactGraphSnapshot
from app.models.ci_v2_risk import RiskAssessment
from app.models.ecr_eco import ECRAttachment, ECRRequest, ECO
from app.models.user import User
from app.schemas import (
    ECRAttachmentOut,
    ECRCreate,
    ECRDetailOut,
    ECROut,
    ECRRejectRequest,
    ECRSummaryOut,
    ECRUpdate,
)
from app.services.events import bus, EventTypes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecr", tags=["ECR"])

# ── 常量 ─────────────────────────────────────────────────────────────

ALLOWED_ATTACHMENT_TYPES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "ecr")


# ── EventStore 辅助 ──────────────────────────────────────────────


def _record_event_store(db, event_type, aggregate_type, aggregate_id, event_data=None, correlation_id=None):
    """非阻断记录事件到 EventStore"""
    try:
        from app.services.event_store_service import EventStoreService
        EventStoreService.record(
            db=db,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            event_data=event_data or {},
            producer=f"{aggregate_type}.api",
        )
    except Exception as e:
        logger.warning("EventStore record 失败 (%s/%s#%s): %s", event_type, aggregate_type, aggregate_id, e)


# ── 辅助函数 ─────────────────────────────────────────────────────────

def _generate_ecr_code(db: Session) -> str:
    """生成 ECR 编号: ECR-YYYYMMDD-XXXX (每日序号从 0001 开始)"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"ECR-{today}-"
    # 查询当日最大序号
    max_code = db.query(func.max(ECRRequest.code)).filter(
        ECRRequest.code.like(f"{prefix}%")
    ).scalar()
    if max_code:
        seq = int(max_code.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _check_ecr_exists(db: Session, ecr_id: int) -> ECRRequest:
    """查询 ECR 并检查是否存在"""
    ecr = db.query(ECRRequest).filter(ECRRequest.id == ecr_id).first()
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    return ecr


def _check_status_transition(current: str, target: str) -> None:
    """检查状态转换是否合法"""
    # 终端状态保护：REJECTED 和 CONVERTED 不可再变更
    TERMINAL_STATES = {ECRStatus.REJECTED.value, ECRStatus.CONVERTED.value}
    if current in TERMINAL_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"终端状态 {current} 不可再变更（Board 裁决: 必须新建 ECR）",
        )

    valid_transitions = {
        ECRStatus.DRAFT.value: [ECRStatus.SUBMITTED.value],
        ECRStatus.SUBMITTED.value: [ECRStatus.DRAFT.value, ECRStatus.REVIEWING.value],
        ECRStatus.REVIEWING.value: [ECRStatus.APPROVED.value, ECRStatus.REJECTED.value],
        ECRStatus.APPROVED.value: [ECRStatus.CONVERTED.value],
        ECRStatus.REJECTED.value: [],  # 终端状态，Board裁决不可再提交
        ECRStatus.CONVERTED.value: [],
    }
    allowed = valid_transitions.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"非法状态转换: {current} → {target}，允许: {allowed}" if allowed else f"状态 {current} 不可变更",
        )


def _get_attachment_count(db: Session, ecr_id: int) -> int:
    """获取 ECR 附件数量"""
    return db.query(func.count(ECRAttachment.id)).filter(
        ECRAttachment.ecr_id == ecr_id
    ).scalar() or 0


# ═══════════════════════════════════════════════════════════════════════
#  创建 ECR 草稿
# ═══════════════════════════════════════════════════════════════════════

@router.post("", response_model=ECROut, summary="创建ECR草稿")
def create_ecr(
    body: ECRCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """创建 ECR 草稿，自动生成编号，状态为 DRAFT"""
    code = _generate_ecr_code(db)

    # 将 JSON 字符串转为 dict（如果前端传的是 str）
    affected_products = body.affected_products
    affected_documents = body.affected_documents
    if isinstance(affected_products, str):
        try:
            affected_products = json.loads(affected_products)
        except (json.JSONDecodeError, TypeError):
            affected_products = affected_products
    if isinstance(affected_documents, str):
        try:
            affected_documents = json.loads(affected_documents)
        except (json.JSONDecodeError, TypeError):
            affected_documents = affected_documents

    ecr = ECRRequest(
        code=code,
        title=body.title,
        ecr_type=body.ecr_type,
        reason=body.reason,
        urgency=body.urgency,
        affected_products=affected_products,
        affected_documents=affected_documents,
        description=body.description,
        status=ECRStatus.DRAFT.value,
        submitter_id=current_user.id,
        submitter_name=current_user.full_name or current_user.username,
        org_id=current_user.org_id,
    )
    db.add(ecr)
    db.commit()
    db.refresh(ecr)

    # 填充附件计数
    ecr_out = _ecr_to_out(ecr, db)
    return ecr_out


# ═══════════════════════════════════════════════════════════════════════
#  列表查询
# ═══════════════════════════════════════════════════════════════════════

@router.get("", response_model=dict, summary="ECR列表查询")
def list_ecrs(
    status: Optional[str] = Query(None, description="状态筛选"),
    ecr_type: Optional[str] = Query(None, description="变更类型筛选"),
    urgency: Optional[str] = Query(None, description="紧急度筛选"),
    submitter_id: Optional[int] = Query(None, description="提交人ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索(标题/编号)"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> dict:
    """查询 ECR 列表，支持状态/类型/紧急度/提交人/关键词/日期范围筛选，分页返回"""
    q = db.query(ECRRequest)

    if status:
        q = q.filter(ECRRequest.status == status)
    if ecr_type:
        q = q.filter(ECRRequest.ecr_type == ecr_type)
    if urgency:
        q = q.filter(ECRRequest.urgency == urgency)
    if submitter_id:
        q = q.filter(ECRRequest.submitter_id == submitter_id)
    if keyword:
        like_pattern = f"%{keyword}%"
        q = q.filter(
            ECRRequest.title.ilike(like_pattern) | ECRRequest.code.ilike(like_pattern)
        )
    if date_from:
        q = q.filter(ECRRequest.created_at >= date_from)
    if date_to:
        q = q.filter(ECRRequest.created_at <= f"{date_to} 23:59:59")

    # 排序
    q = q.order_by(ECRRequest.created_at.desc())

    # 分页
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # 构建输出
    out_items = []
    for ecr in items:
        att_count = _get_attachment_count(db, ecr.id)
        out_items.append(ECROut(
            id=ecr.id,
            code=ecr.code,
            title=ecr.title,
            ecr_type=ecr.ecr_type,
            reason=ecr.reason,
            urgency=ecr.urgency,
            affected_products=ecr.affected_products,
            affected_documents=ecr.affected_documents,
            description=ecr.description,
            status=ecr.status,
            workflow_id=ecr.workflow_id,
            submitter_id=ecr.submitter_id,
            submitter_name=ecr.submitter_name,
            reviewer_id=ecr.reviewer_id,
            reviewed_at=ecr.reviewed_at,
            rejection_reason=ecr.rejection_reason,
            org_id=ecr.org_id,
            created_at=ecr.created_at,
            updated_at=ecr.updated_at,
            attachment_count=att_count,
        ))

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": out_items,
    }


# ═══════════════════════════════════════════════════════════════════════
#  ECR 详情
# ═══════════════════════════════════════════════════════════════════════

@router.get("/{ecr_id}", response_model=ECRDetailOut, summary="ECR详情")
def get_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECRDetailOut:
    """获取 ECR 详情，含附件列表和关联的 ECO 信息"""
    ecr = _check_ecr_exists(db, ecr_id)

    # 附件列表
    attachments = db.query(ECRAttachment).filter(
        ECRAttachment.ecr_id == ecr_id
    ).order_by(ECRAttachment.created_at.desc()).all()

    # 关联 ECO
    eco = db.query(ECO).filter(ECO.ecr_id == ecr_id).first()
    eco_code = eco.code if eco else None
    eco_id = eco.id if eco else None
    eco_status = eco.status if eco else None

    att_count = _get_attachment_count(db, ecr_id)

    # CIE v2.0: 查询关联风险评估和影响图
    ci_risk = db.query(RiskAssessment).filter(
        RiskAssessment.ecr_id == ecr_id
    ).order_by(RiskAssessment.created_at.desc()).first()
    ci_graph = db.query(ImpactGraphSnapshot).filter(
        ImpactGraphSnapshot.ecr_id == ecr_id
    ).order_by(ImpactGraphSnapshot.created_at.desc()).first()

    return ECRDetailOut(
        id=ecr.id,
        code=ecr.code,
        title=ecr.title,
        ecr_type=ecr.ecr_type,
        reason=ecr.reason,
        urgency=ecr.urgency,
        affected_products=ecr.affected_products,
        affected_documents=ecr.affected_documents,
        description=ecr.description,
        status=ecr.status,
        workflow_id=ecr.workflow_id,
        submitter_id=ecr.submitter_id,
        submitter_name=ecr.submitter_name,
        reviewer_id=ecr.reviewer_id,
        reviewed_at=ecr.reviewed_at,
        rejection_reason=ecr.rejection_reason,
        org_id=ecr.org_id,
        created_at=ecr.created_at,
        updated_at=ecr.updated_at,
        attachment_count=att_count,
        attachments=[
            ECRAttachmentOut.model_validate(a) for a in attachments
        ],
        eco_code=eco_code,
        eco_id=eco_id,
        eco_status=eco_status,
        risk_assessment_id=ci_risk.id if ci_risk else None,
        risk_score=float(ci_risk.risk_score) if ci_risk else None,
        risk_level=ci_risk.risk_level if ci_risk else None,
        impact_graph_id=ci_graph.id if ci_graph else None,
        ripple_score=float(ci_graph.ripple_score) if ci_graph else None,
    )


# ═══════════════════════════════════════════════════════════════════════
#  更新 ECR（仅 DRAFT）
# ═══════════════════════════════════════════════════════════════════════

@router.put("/{ecr_id}", response_model=ECROut, summary="更新ECR")
def update_ecr(
    ecr_id: int,
    body: ECRUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """更新 ECR 草稿（仅 DRAFT 状态允许更新）"""
    ecr = _check_ecr_exists(db, ecr_id)
    if ecr.status != ECRStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="仅草稿状态可编辑")

    # 字段映射
    update_fields = {
        "title": body.title,
        "ecr_type": body.ecr_type,
        "reason": body.reason,
        "urgency": body.urgency,
        "description": body.description,
    }
    for field, value in update_fields.items():
        if value is not None:
            setattr(ecr, field, value)

    # JSON 字段特殊处理
    if body.affected_products is not None:
        try:
            ecr.affected_products = json.loads(body.affected_products) if isinstance(body.affected_products, str) else body.affected_products
        except (json.JSONDecodeError, TypeError):
            ecr.affected_products = body.affected_products
    if body.affected_documents is not None:
        try:
            ecr.affected_documents = json.loads(body.affected_documents) if isinstance(body.affected_documents, str) else body.affected_documents
        except (json.JSONDecodeError, TypeError):
            ecr.affected_documents = body.affected_documents

    db.commit()
    db.refresh(ecr)

    att_count = _get_attachment_count(db, ecr.id)
    out = _ecr_to_out_full(ecr, att_count)
    return out


# ═══════════════════════════════════════════════════════════════════════
#  删除 ECR（仅 DRAFT）
# ═══════════════════════════════════════════════════════════════════════

@router.delete("/{ecr_id}", summary="删除ECR")
def delete_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> dict:
    """删除 ECR 草稿（仅 DRAFT 状态允许删除）"""
    ecr = _check_ecr_exists(db, ecr_id)
    if ecr.status != ECRStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="仅草稿状态可删除")

    # 清理附件文件
    attachments = db.query(ECRAttachment).filter(ECRAttachment.ecr_id == ecr_id).all()
    for att in attachments:
        if att.file_path and os.path.exists(att.file_path):
            try:
                os.remove(att.file_path)
            except OSError:
                pass

    db.delete(ecr)
    db.commit()
    return {"ok": True, "message": "ECR 已删除"}

# ── 审批工作流已拆分到 ecr_workflow.py ──
# ── 附件管理已拆分到 ecr_attachments.py ──


# ── 内部辅助：构建 ECROut ──────────────────────────────────────────

def _ecr_to_out(ecr: ECRRequest, db: Session) -> ECROut:
    """将 ECR ORM 对象转为 ECROut（含附件计数）"""
    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


def _ecr_to_out_full(ecr: ECRRequest, att_count: int) -> ECROut:
    """将 ECR ORM 对象转为 ECROut"""
    return ECROut(
        id=ecr.id,
        code=ecr.code,
        title=ecr.title,
        ecr_type=ecr.ecr_type,
        reason=ecr.reason,
        urgency=ecr.urgency,
        affected_products=ecr.affected_products,
        affected_documents=ecr.affected_documents,
        description=ecr.description,
        status=ecr.status,
        workflow_id=ecr.workflow_id,
        submitter_id=ecr.submitter_id,
        submitter_name=ecr.submitter_name,
        reviewer_id=ecr.reviewer_id,
        reviewed_at=ecr.reviewed_at,
        rejection_reason=ecr.rejection_reason,
        org_id=ecr.org_id,
        created_at=ecr.created_at,
        updated_at=ecr.updated_at,
        attachment_count=att_count,
    )
