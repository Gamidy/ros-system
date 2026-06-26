"""密码重置API — 基于令牌的密码找回"""
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, require_role, get_current_user
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.schemas import (
    ForgotPasswordRequest,
    VerifyResetTokenRequest,
    AdminResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["认证"])

# 重置令牌有效期（小时）
RESET_TOKEN_EXPIRE_HOURS = 24


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """忘记密码 — 通过用户名发起重置

    不暴露用户是否存在，总是返回相同消息。
    如果用户存在，生成重置令牌并持久化到数据库。
    """
    # 总是返回相同的消息，不暴露用户是否存在
    message = {"message": "如果用户存在，重置链接已生成"}

    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        return message

    # 生成唯一令牌
    token_str = str(uuid.uuid4()) + str(uuid.uuid4()).replace("-", "")

    # 计算过期时间
    expires_at = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_token)
    db.commit()

    return message


@router.post("/verify-reset-token")
def verify_reset_token(req: VerifyResetTokenRequest, db: Session = Depends(get_db)) -> dict:
    """验证重置令牌 — 验证token有效期 → 更新密码 → 标记token已使用"""
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False,
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="令牌无效或已使用")

    # 检查有效期
    now = datetime.now(timezone.utc)
    if reset_token.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="令牌已过期，请重新申请")

    # 查找对应用户
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")

    # 更新密码
    user.hashed_password = get_password_hash(req.new_password)

    # 标记令牌已使用
    reset_token.used = True

    db.commit()

    return {"message": "密码重置成功"}


@router.post("/admin-reset-password")
def admin_reset_password(
    req: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> dict:
    """管理员直接重置用户密码 — 仅限 admin 角色"""
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = get_password_hash(req.new_password)
    db.commit()

    return {"message": "密码已重置"}
