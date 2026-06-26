"""认证与用户管理 — Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ═══════════════ 用户认证 ═══════════════

class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "engineer"


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool = True
    created_at: datetime
    allowed_menus: list[str] = []
    allowed_paths: list[str] = []  # 前端路由路径（如 /dashboard），由服务端动态下发
    class Config: from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ═══════════════ 账号申请 ═══════════════

class AccountApplicationCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6)
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    reason: Optional[str] = Field(default=None, max_length=500)
    role: str = "engineer"  # 申请注册角色，仅允许非特权角色


class AccountApplicationOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    application_reason: Optional[str] = None
    application_status: str
    role: str
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True


class AccountApplicationReview(BaseModel):
    action: str  # approve | reject


# ═══════════════ 密码管理 ═══════════════

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class ForgotPasswordRequest(BaseModel):
    """忘记密码 — 通过用户名发起重置"""
    username: str


class VerifyResetTokenRequest(BaseModel):
    """验证重置令牌并设置新密码"""
    token: str
    new_password: str = Field(min_length=6)


class AdminResetPasswordRequest(BaseModel):
    """管理员直接重置用户密码"""
    user_id: int
    new_password: str = Field(min_length=6)
