"""认证API"""
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user, require_role, invalidate_token, oauth2_scheme
from app.core.permissions import get_allowed_menus, get_allowed_paths, is_valid_role
from app.models.user import User
from app.models.approval import ApprovalChain, ApprovalRequest
from app.schemas import (
    LoginRequest, Token, UserCreate, UserOut,
    AccountApplicationCreate, AccountApplicationOut, AccountApplicationReview,
    ChangePasswordRequest, ForgotPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Token)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(access_token=token)


@router.post("/logout")
def logout(token: str = Security(oauth2_scheme)):
    """登出：将当前 token 加入黑名单使其失效"""
    invalidate_token(token)
    return {"message": "已登出"}


def _require_admin_for_register():
    if settings.ALLOW_PUBLIC_REGISTER:
        def _noop():
            return None
        return _noop
    return require_role("admin")


@router.post("/register", response_model=UserOut)
def register(
    req: UserCreate,
    db: Session = Depends(get_db),
    _admin_check: Optional[User] = Depends(_require_admin_for_register()),
):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 接受请求中的 role 参数，但禁止 admin 和 general_manager 特权角色
    role = req.role if req.role and req.role not in ("admin", "general_manager") else "engineer"
    # 确保角色在合法角色列表中
    if not is_valid_role(role):
        role = "engineer"
    user = User(
        username=req.username,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        email=req.email,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _enrich_user_out(user)


@router.post("/apply", response_model=AccountApplicationOut)
def apply_account(req: AccountApplicationCreate, db: Session = Depends(get_db)):
    """账号申请 — 开放接口，无需登录"""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if req.email and db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被占用")

    user = User(
        username=req.username,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        email=req.email,
        department=req.department,
        position=req.position,
        phone=req.phone,
        application_reason=req.reason,
        application_status="pending",
        role=req.role if req.role and req.role not in ("admin", "general_manager") and is_valid_role(req.role) else "engineer",
        is_active=False,
    )
    db.add(user)
    db.flush()  # 获取 user.id

    # 查找账号申请审批链（code = 'account_apply'）
    chain = db.query(ApprovalChain).filter(ApprovalChain.code == "account_register").first()
    if chain:
        approval_req = ApprovalRequest(
            chain_id=chain.id,
            request_type="register",
            request_id=user.id,
            title=f"账号申请: {req.username}",
            requester=req.username or req.full_name or req.username,
            status="pending",
        )
        db.add(approval_req)

    db.commit()
    db.refresh(user)
    return user


@router.get("/applications", response_model=list[AccountApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """管理员查看所有账号申请"""
    return (
        db.query(User)
        .filter(User.application_status.in_(["pending", "approved", "rejected"]))
        .order_by(User.created_at.desc())
        .all()
    )


@router.patch("/applications/{user_id}/review", response_model=AccountApplicationOut)
def review_application(
    user_id: int,
    req: AccountApplicationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """管理员审核账号申请"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.application_status != "pending":
        raise HTTPException(status_code=400, detail="该申请已被审核")

    if req.action == "approve":
        user.application_status = "approved"
        user.is_active = True
    elif req.action == "reject":
        user.application_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")

    # 更新关联的审批请求
    approval_req = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.request_type == "register",
            ApprovalRequest.request_id == user.id,
            ApprovalRequest.status == "pending",
        )
        .first()
    )
    if approval_req:
        approval_req.status = req.action + "d"  # approved / rejected

    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _enrich_user_out(current_user)


@router.put("/password")
def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前用户密码"""
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """忘记密码 — 通过手机号+真实姓名验证后重置密码

    验证通过后生成新密码，仅返回成功提示（不返回密码明文）。
    密码将通过短信/邮件发送（待对接）。
    """
    user = db.query(User).filter(User.phone == req.phone).first()
    if not user or user.full_name != req.full_name:
        # 统一返回 200，不区分手机号/姓名错误，防止枚举
        return {"message": "验证通过后密码已重置，请联系管理员获取新密码"}
    # 生成12位随机密码
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    # TODO: 对接短信/邮件发送 new_password
    return {"message": "密码已重置，请查收短信或联系管理员"}


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
):
    return [_enrich_user_out(u) for u in db.query(User).all()]


def _enrich_user_out(user: User) -> UserOut:
    """将 User 模型转换为包含 allowed_menus 和 allowed_paths 的 UserOut"""
    menus = get_allowed_menus(user.role)
    paths = get_allowed_paths(user.role)
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        allowed_menus=menus,
        allowed_paths=paths,
    )
