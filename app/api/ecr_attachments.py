"""ECR附件管理 API — 从 ecr.py 拆分"""
import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_menu
from app.core.security import get_current_user
from app.models.ecr_eco import ECRAttachment, ECRRequest
from app.models.user import User
from app.schemas import ECRAttachmentOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecr", tags=["ECR"])

# ── 常量 ─────────────────────────────────────────────────────────────

ALLOWED_ATTACHMENT_TYPES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "ecr")


# ── 辅助函数 ─────────────────────────────────────────────────────────


def _check_ecr_exists(db: Session, ecr_id: int) -> ECRRequest:
    """查询 ECR 并检查是否存在"""
    ecr = db.query(ECRRequest).filter(ECRRequest.id == ecr_id).first()
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    return ecr


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
