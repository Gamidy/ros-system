"""认证与用户管理 — Pydantic Schema"""

import re
from typing import Annotated, Optional
from datetime import datetime

from pydantic import BaseModel, Field, AfterValidator


def validate_password_strength(password: str) -> str:
    """密码强度校验: ≥8位, 含大小写字母+数字+特殊字符"""
    if len(password) < 8:
        raise ValueError("密码至少需要8位")
    if not re.search(r"[A-Z]", password):
        raise ValueError("密码需要至少一个大写字母")
    if not re.search(r"[a-z]", password):
        raise ValueError("密码需要至少一个小写字母")
    if not re.search(r"\d", password):
        raise ValueError("密码需要至少一个数字")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("密码需要至少一个特殊字符")
    return password


# ═══════════════ 通用类型 ═══════════════

PasswordStr = Annotated[str, AfterValidator(validate_password_strength)]


# ═══════════════ 用户认证 ═══════════════

class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: PasswordStr
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
    new_password: PasswordStr


class ForgotPasswordRequest(BaseModel):
    """忘记密码 — 通过用户名发起重置"""
    username: str


class VerifyResetTokenRequest(BaseModel):
    """验证重置令牌并设置新密码"""
    token: str
    new_password: PasswordStr


class AdminResetPasswordRequest(BaseModel):
    """管理员直接重置用户密码"""
    user_id: int
    new_password: PasswordStr
