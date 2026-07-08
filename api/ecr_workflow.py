"""ECR审批工作流 API — 从 ecr.py 拆分（状态转换 + 转ECO）"""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import ECRStatus, ECOStatus
from app.core.permissions import require_menu
from app.core.security import get_current_user
from app.models.approval import ApprovalRequest
from app.models.ecr_eco import ECRAttachment, ECRRequest, ECO
from app.models.user import User
from app.schemas import ECRDetailOut, ECROut, ECRRejectRequest, ECRAttachmentOut
from app.services.events import bus, EventTypes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecr", tags=["ECR"])


# ── EventStore 辅助 ──────────────────────────────────────────────


def _record_event_store(db: Session, event_type: str, aggregate_type: str, aggregate_id: int,
                         event_data: dict | None = None, correlation_id: str | None = None) -> None:
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


def _check_ecr_exists(db: Session, ecr_id: int) -> ECRRequest:
    """查询 ECR 并检查是否存在"""
    ecr = db.query(ECRRequest).filter(ECRRequest.id == ecr_id).first()
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    return ecr


def _check_status_transition(current: str, target: str) -> None:
    """检查状态转换是否合法"""
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
        ECRStatus.REJECTED.value: [],
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


def _ecr_to_out(ecr: ECRRequest, db: Session) -> ECROut:
    """将 ECR ORM 对象转为 ECROut（含附件计数）"""
    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


# ═══════════════════════════════════════════════════════════════════════
#  提交审批（DRAFT → SUBMITTED）
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/submit", response_model=ECROut, summary="提交审批")
def submit_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """提交 ECR 审批：状态 DRAFT → SUBMITTED，创建对应的 ApprovalRequest"""
    ecr = _check_ecr_exists(db, ecr_id)
    _check_status_transition(ecr.status, ECRStatus.SUBMITTED.value)

    ecr.status = ECRStatus.SUBMITTED.value

    # 创建审批请求
    approval_req = ApprovalRequest(
        chain_id=1,
        request_type="ecr",
        request_id=ecr.id,
        title=f"ECR审批: {ecr.code} - {ecr.title}",
        requester=current_user.full_name or current_user.username,
        status="pending",
        current_step=1,
        org_id=current_user.org_id,
    )
    db.add(approval_req)
    db.flush()

    ecr.workflow_id = approval_req.id
    db.commit()
    db.refresh(ecr)

    # === CIE v2.0 Hook: 提交时自动触发风险评分 (非阻断) ===
    try:
        from app.services.ai.risk_engine import RiskEngine
        risk_engine = RiskEngine()
        risk_engine.assess_for_ecr(db=db, ecr_id=ecr.id)
        logger.info("ECR %s (%s) 提交后自动风险评分完成", ecr.id, ecr.code)
    except Exception as e:
        logger.warning("ECR %s 风险评分触发失败 (非致命): %s", ecr.id, e)

    # ── EventStore 记录 ──
    correlation_id = str(uuid.uuid4())
    _record_event_store(db, "ecr.submitted", "ecr", ecr.id,
                        event_data={"code": ecr.code, "title": ecr.title},
                        correlation_id=correlation_id)

    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


# ═══════════════════════════════════════════════════════════════════════
#  撤回（SUBMITTED → DRAFT）
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/withdraw", response_model=ECROut, summary="撤回审批")
def withdraw_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """撤回 ECR 审批：状态 SUBMITTED → DRAFT，关闭 ApprovalRequest"""
    ecr = _check_ecr_exists(db, ecr_id)
    _check_status_transition(ecr.status, ECRStatus.DRAFT.value)

    # 关闭审批请求
    if ecr.workflow_id:
        approval_req = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == ecr.workflow_id
        ).first()
        if approval_req and approval_req.status == "pending":
            approval_req.status = "rejected"

    ecr.status = ECRStatus.DRAFT.value
    db.commit()
    db.refresh(ecr)

    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


# ═══════════════════════════════════════════════════════════════════════
#  开始评审（SUBMITTED → REVIEWING）
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/review", response_model=ECROut, summary="开始评审")
def review_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """开始评审 ECR：状态 SUBMITTED → REVIEWING"""
    ecr = _check_ecr_exists(db, ecr_id)
    _check_status_transition(ecr.status, ECRStatus.REVIEWING.value)

    ecr.status = ECRStatus.REVIEWING.value
    ecr.reviewer_id = current_user.id
    db.commit()
    db.refresh(ecr)

    # ── EventStore 记录 ──
    _record_event_store(db, "ecr.reviewing", "ecr", ecr.id,
                        event_data={"code": ecr.code})

    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


# ═══════════════════════════════════════════════════════════════════════
#  批准（REVIEWING → APPROVED）
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/approve", response_model=ECROut, summary="批准ECR")
def approve_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """批准 ECR：状态 REVIEWING → APPROVED，同步更新 ApprovalRequest 状态"""
    ecr = _check_ecr_exists(db, ecr_id)
    _check_status_transition(ecr.status, ECRStatus.APPROVED.value)

    ecr.status = ECRStatus.APPROVED.value
    ecr.reviewer_id = current_user.id
    ecr.reviewed_at = datetime.now(timezone.utc)

    # 更新审批请求状态
    if ecr.workflow_id:
        approval_req = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == ecr.workflow_id
        ).first()
        if approval_req:
            approval_req.status = "approved"

    db.commit()
    db.refresh(ecr)

    # === CIE v2.0 Hook: emit 审批通过事件 ===
    try:
        bus.emit_async(
            EventTypes.ECR_APPROVED,
            ecr_id=ecr.id,
            risk_score=None,
        )
    except Exception as e:
        logger.warning("emit ECR_APPROVED 失败 (非致命): %s", e)

    # ── EventStore 记录 ──
    _record_event_store(db, "ecr.approved", "ecr", ecr.id,
                        event_data={"code": ecr.code})

    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


# ═══════════════════════════════════════════════════════════════════════
#  驳回（REVIEWING → REJECTED）
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/reject", response_model=ECROut, summary="驳回ECR")
def reject_ecr(
    ecr_id: int,
    body: ECRRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECROut:
    """驳回 ECR：状态 REVIEWING → REJECTED，需要提供驳回原因"""
    ecr = _check_ecr_exists(db, ecr_id)
    _check_status_transition(ecr.status, ECRStatus.REJECTED.value)

    ecr.status = ECRStatus.REJECTED.value
    ecr.reviewer_id = current_user.id
    ecr.reviewed_at = datetime.now(timezone.utc)
    ecr.rejection_reason = body.rejection_reason

    # 更新审批请求状态
    if ecr.workflow_id:
        approval_req = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == ecr.workflow_id
        ).first()
        if approval_req:
            approval_req.status = "rejected"

    db.commit()
    db.refresh(ecr)

    # === CIE v2.0 Hook: emit 驳回事件 ===
    try:
        bus.emit_async(
            EventTypes.ECR_REJECTED,
            ecr_id=ecr.id,
            rejection_reason=ecr.rejection_reason,
        )
    except Exception as e:
        logger.warning("emit ECR_REJECTED 失败 (非致命): %s", e)

    # ── EventStore 记录 ──
    _record_event_store(db, "ecr.rejected", "ecr", ecr.id,
                        event_data={"code": ecr.code, "reason": ecr.rejection_reason})

    att_count = _get_attachment_count(db, ecr.id)
    return _ecr_to_out_full(ecr, att_count)


# ═══════════════════════════════════════════════════════════════════════
#  转 ECO（APPROVED → CONVERTED）
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/convert", response_model=ECRDetailOut, summary="转ECO")
def convert_ecr(
    ecr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECRDetailOut:
    """将已批准的 ECR 转为 ECO 草稿：APPROVED → CONVERTED"""
    ecr = _check_ecr_exists(db, ecr_id)
    _check_status_transition(ecr.status, ECRStatus.CONVERTED.value)

    # 检查是否已有关联 ECO
    existing_eco = db.query(ECO).filter(ECO.ecr_id == ecr_id).first()
    if existing_eco:
        raise HTTPException(status_code=400, detail="该 ECR 已转为 ECO")

    # 生成 ECO 编号
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    eco_prefix = f"ECO-{today}-"
    max_eco_code = db.query(func.max(ECO.code)).filter(
        ECO.code.like(f"{eco_prefix}%")
    ).scalar()
    if max_eco_code:
        eco_seq = int(max_eco_code.split("-")[-1]) + 1
    else:
        eco_seq = 1
    eco_code = f"{eco_prefix}{eco_seq:04d}"

    # 创建 ECO 草稿
    eco = ECO(
        code=eco_code,
        ecr_id=ecr.id,
        title=ecr.title,
        change_summary=f"源自 ECR: {ecr.code}\n原因: {ecr.reason}\n描述: {ecr.description or ''}",
        status=ECOStatus.DRAFT.value,
        created_by=current_user.id,
        org_id=current_user.org_id,
    )
    db.add(eco)
    db.flush()

    ecr.status = ECRStatus.CONVERTED.value
    db.commit()
    db.refresh(ecr)

    # 构造详情响应
    attachments = db.query(ECRAttachment).filter(
        ECRAttachment.ecr_id == ecr_id
    ).order_by(ECRAttachment.created_at.desc()).all()

    att_count = _get_attachment_count(db, ecr.id)

    # ── EventStore 记录 ──
    _record_event_store(db, "ecr.converted", "ecr", ecr.id,
                        event_data={"code": ecr.code, "eco_code": eco_code})

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
        eco_code=eco.code,
        eco_id=eco.id,
        eco_status=eco.status,
    )
