from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.core.security import get_current_user, get_password_hash, verify_password, create_access_token, create_refresh_token
from app.models import User, Role, Permission, Tenant
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse, RoleCreate, RoleResponse

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户登录"""
    # 查找用户
    user = db.query(User).filter(
        func.lower(User.username) == func.lower(data.username),
        User.deleted_at.is_(None)
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账户已被禁用")
    
    # 更新最后登录时间
    user.last_login_at = func.now()
    db.commit()
    
    # 创建令牌
    access_token = create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800
    )

@router.post("/register")
async def register(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册（仅用于初始化）"""
    # 检查租户是否存在
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # 检查用户名是否已存在
    existing = db.query(User).filter(
        User.tenant_id == data.tenant_id,
        func.lower(User.username) == func.lower(data.username)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    user = User(
        tenant_id=data.tenant_id,
        username=data.username,
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        department=data.department,
        title=data.title,
        phone=data.phone
    )
    db.add(user)
    db.flush()
    
    # 分配角色
    if data.role_ids:
        for role_id in data.role_ids:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                user.roles.append(role)
    
    db.commit()
    db.refresh(user)
    
    return {"message": "注册成功", "user_id": user.id}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    roles = []
    for role in current_user.roles:
        roles.append({
            "id": str(role.id),
            "code": role.code,
            "name": role.name
        })
    
    return UserResponse(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        department=current_user.department,
        title=current_user.title,
        phone=current_user.phone,
        status=current_user.status,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        roles=roles
    )

@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    from app.core.security import decode_token
    
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    
    new_access_token = create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=1800
    )

@router.post("/init")
async def init_system(
    db: Session = Depends(get_db)
):
    """初始化系统（创建默认租户、管理员账号、权限）"""
    # 检查是否已初始化
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        raise HTTPException(status_code=400, detail="系统已初始化")
    
    # 获取或创建默认租户
    tenant = db.query(Tenant).filter(Tenant.code == "default").first()
    if not tenant:
        tenant = Tenant(code="default", name="默认租户", description="系统默认租户")
        db.add(tenant)
        db.flush()
    
    # 创建管理员角色
    admin_role = db.query(Role).filter(
        Role.tenant_id == tenant.id,
        Role.code == "admin"
    ).first()
    if not admin_role:
        admin_role = Role(
            tenant_id=tenant.id,
            code="admin",
            name="系统管理员",
            description="拥有所有权限",
            is_system=True
        )
        db.add(admin_role)
        db.flush()
    
    # 获取所有权限并分配给管理员角色
    permissions = db.query(Permission).all()
    for perm in permissions:
        if perm not in admin_role.permissions:
            admin_role.permissions.append(perm)
    
    # 创建管理员用户
    admin_user = User(
        tenant_id=tenant.id,
        username="admin",
        email="admin@plm.local",
        password_hash=get_password_hash("admin123"),
        full_name="系统管理员",
        status="active"
    )
    db.add(admin_user)
    db.flush()
    
    admin_user.roles.append(admin_role)
    db.commit()
    
    return {
        "message": "系统初始化成功",
        "admin_username": "admin",
        "admin_password": "admin123",
        "tenant_id": str(tenant.id)
    }
