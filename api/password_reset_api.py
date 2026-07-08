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


# 已废弃 — forgot_password 移至 auth.py
# 前端使用 /auth/forgot-password（auth.py）带 email 参数
# 此文件保留 verify-reset-token 和 admin-reset-password


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
        raise HTTPException(status_code=400, detail="无效的凭据")

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
