"""认证API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user, require_role
from app.models.user import User
from app.models.approval import ApprovalChain, ApprovalRequest
from app.schemas import (
    LoginRequest, Token, UserCreate, UserOut,
    AccountApplicationCreate, AccountApplicationOut, AccountApplicationReview,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Token)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(access_token=token)


@router.post("/register", response_model=UserOut)
def register(req: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=req.username,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        email=req.email,
        role=req.role or "engineer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
        role="engineer",
        is_active=False,
    )
    db.add(user)
    db.flush()  # 获取 user.id

    # 查找账号申请审批链（code = 'account_apply'）
    chain = db.query(ApprovalChain).filter(ApprovalChain.code == "account_apply").first()
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
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(User).all()
