"""Phase 6 S3 — ECR (Engineering Change Request) 工程变更申请 API"""
import json
import os
import shutil
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

router = APIRouter(prefix="/api/ecr", tags=["ECR"])

# ── 常量 ─────────────────────────────────────────────────────────────

ALLOWED_ATTACHMENT_TYPES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "ecr")


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
    valid_transitions = {
        ECRStatus.DRAFT.value: [ECRStatus.SUBMITTED.value],
        ECRStatus.SUBMITTED.value: [ECRStatus.DRAFT.value, ECRStatus.REVIEWING.value],
        ECRStatus.REVIEWING.value: [ECRStatus.APPROVED.value, ECRStatus.REJECTED.value],
        ECRStatus.APPROVED.value: [ECRStatus.CONVERTED.value],
        ECRStatus.REJECTED.value: [ECRStatus.DRAFT.value],
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
        chain_id=1,  # 使用默认审批链
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

    att_count = _get_attachment_count(db, ecr.id)
    out = _ecr_to_out_full(ecr, att_count)
    return out


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
    out = _ecr_to_out_full(ecr, att_count)
    return out


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

    att_count = _get_attachment_count(db, ecr.id)
    out = _ecr_to_out_full(ecr, att_count)
    return out


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

    att_count = _get_attachment_count(db, ecr.id)
    out = _ecr_to_out_full(ecr, att_count)
    return out


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

    att_count = _get_attachment_count(db, ecr.id)
    out = _ecr_to_out_full(ecr, att_count)
    return out


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


# ═══════════════════════════════════════════════════════════════════════
#  上传附件
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{ecr_id}/attachments", response_model=ECRAttachmentOut, summary="上传附件")
async def upload_attachment(
    ecr_id: int,
    file: UploadFile = File(..., description="附件文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECRAttachmentOut:
    """为 ECR 上传附件（任意状态均可上传）"""
    ecr = _check_ecr_exists(db, ecr_id)

    # 验证文件类型
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext and ext not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，允许: {', '.join(sorted(ALLOWED_ATTACHMENT_TYPES))}",
        )

    # 验证文件大小
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)",
        )

    # 确保上传目录存在
    upload_dir = os.path.join(UPLOAD_DIR, str(ecr_id))
    os.makedirs(upload_dir, exist_ok=True)

    # 保存文件（防重名）
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 创建附件记录
    attachment = ECRAttachment(
        ecr_id=ecr.id,
        file_name=file.filename or safe_filename,
        file_path=file_path,
        file_type=ext.lstrip(".") if ext else None,
        file_size=len(file_content),
        uploaded_by=current_user.full_name or current_user.username,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return ECRAttachmentOut.model_validate(attachment)


# ═══════════════════════════════════════════════════════════════════════
#  删除附件
# ═══════════════════════════════════════════════════════════════════════

@router.delete("/{ecr_id}/attachments/{att_id}", summary="删除附件")
def delete_attachment(
    ecr_id: int,
    att_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> dict:
    """删除 ECR 的指定附件"""
    # 验证 ECR 存在
    _check_ecr_exists(db, ecr_id)

    attachment = db.query(ECRAttachment).filter(
        ECRAttachment.id == att_id,
        ECRAttachment.ecr_id == ecr_id,
    ).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    # 删除物理文件
    if attachment.file_path and os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except OSError:
            pass

    db.delete(attachment)
    db.commit()
    return {"ok": True, "message": "附件已删除"}


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
