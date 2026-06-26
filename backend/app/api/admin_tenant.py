"""多租户组织管理API — 组织CRUD、成员管理、当前用户组织信息"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.organization import Organization, OrganizationMember
from app.models.user import User

# ── 路由 ─────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/admin/tenants", tags=["组织管理"])
auth_router = APIRouter(prefix="/api/auth", tags=["认证"])

# ── Pydantic Schemas ─────────────────────────────────────────────


class OrgCreate(BaseModel):
    """创建组织请求"""
    name: str = Field(..., min_length=1, max_length=200, description="组织名称")
    code: str = Field(..., min_length=1, max_length=50, description="组织编码（唯一标识）")
    contact_email: Optional[str] = Field(None, max_length=100, description="联系邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    max_users: int = Field(100, ge=1, le=10000, description="最大用户数限制")


class OrgUpdate(BaseModel):
    """更新组织请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="组织名称")
    contact_email: Optional[str] = Field(None, max_length=100, description="联系邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    max_users: Optional[int] = Field(None, ge=1, le=10000, description="最大用户数限制")
    is_active: Optional[bool] = Field(None, description="是否启用")


class OrgOut(BaseModel):
    """组织信息响应"""
    id: int
    name: str
    code: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    max_users: int
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgMemberAdd(BaseModel):
    """添加成员请求"""
    user_id: int = Field(..., description="用户ID")
    role_in_org: str = Field("member", pattern="^(admin|member)$", description="组织内角色")


class OrgMemberRoleUpdate(BaseModel):
    """修改成员角色请求"""
    role_in_org: str = Field(..., pattern="^(admin|member)$", description="组织内角色")


class OrgMemberOut(BaseModel):
    """组织成员信息响应"""
    id: int
    org_id: int
    user_id: int
    role_in_org: str
    username: str = ""
    full_name: Optional[str] = None
    email: Optional[str] = None
    joined_at: datetime

    class Config:
        from_attributes = True


class MyOrgOut(BaseModel):
    """当前用户所属组织信息响应"""
    id: int
    name: str
    code: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    max_users: int
    member_count: int = 0
    is_org_admin: bool = False
    role_in_org: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════ 组织 CRUD ═══════════════════


@router.post("", response_model=OrgOut)
def create_org(
    req: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
) -> dict:
    """创建组织（仅admin/general_manager可操作）"""
    # 检查编码唯一性
    existing = db.query(Organization).filter(Organization.code == req.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"组织编码 '{req.code}' 已存在")

    org = Organization(
        name=req.name,
        code=req.code,
        contact_email=req.contact_email,
        phone=req.phone,
        address=req.address,
        max_users=req.max_users,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return _enrich_org_out(org, db)


@router.get("", response_model=list[OrgOut])
def list_orgs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（名称/编码）"),
) -> list:
    """获取组织列表（分页，支持关键词搜索）"""
    query = db.query(Organization).filter(Organization.is_active == True)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            Organization.name.like(like) | Organization.code.like(like)
        )
    orgs = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()
    return [_enrich_org_out(o, db) for o in orgs]


@router.get("/{org_id}", response_model=OrgOut)
def get_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取组织详情"""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")
    return _enrich_org_out(org, db)


@router.patch("/{org_id}", response_model=OrgOut)
def update_org(
    org_id: int,
    req: OrgUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
) -> dict:
    """更新组织信息（仅admin/general_manager可操作）"""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return _enrich_org_out(org, db)


@router.delete("/{org_id}")
def delete_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
) -> dict:
    """删除组织（软删除，仅admin/general_manager可操作）"""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")
    if not org.is_active:
        raise HTTPException(status_code=400, detail="组织已被删除")

    org.is_active = False
    db.commit()
    return {"ok": True, "message": "组织已删除"}


# ═══════════════════ 成员管理 ═══════════════════


@router.post("/{org_id}/members", response_model=OrgMemberOut)
def add_member(
    org_id: int,
    req: OrgMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
) -> dict:
    """向组织添加成员（仅admin/general_manager可操作）"""
    # 检查组织存在且启用
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")
    if not org.is_active:
        raise HTTPException(status_code=400, detail="组织已禁用")

    # 检查用户存在且启用
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已禁用")

    # 检查用户上限
    current_member_count = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id
    ).count()
    if current_member_count >= org.max_users:
        raise HTTPException(
            status_code=400,
            detail=f"组织成员已达上限 ({org.max_users})",
        )

    # 检查是否已是成员
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id,
        OrganizationMember.user_id == req.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已是组织成员")

    member = OrganizationMember(
        org_id=org_id,
        user_id=req.user_id,
        role_in_org=req.role_in_org,
    )
    # 同步更新 User 表的 org_id 和 is_org_admin
    user.org_id = org_id
    user.is_org_admin = (req.role_in_org == "admin")

    db.add(member)
    db.commit()
    db.refresh(member)
    return _enrich_member_out(member, db)


@router.get("/{org_id}/members", response_model=list[OrgMemberOut])
def list_members(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
) -> list:
    """获取组织成员列表"""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="组织不存在")

    members = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.org_id == org_id)
        .order_by(OrganizationMember.joined_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_enrich_member_out(m, db) for m in members]


@router.delete("/{org_id}/members/{user_id}")
def remove_member(
    org_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
) -> dict:
    """从组织移除成员（仅admin/general_manager可操作）"""
    member = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id,
        OrganizationMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="该用户不是组织成员")

    # 同步清理 User 表的 org_id 和 is_org_admin
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.org_id = None
        user.is_org_admin = False

    db.delete(member)
    db.commit()
    return {"ok": True, "message": "成员已移除"}


@router.patch("/{org_id}/members/{user_id}/role", response_model=OrgMemberOut)
def update_member_role(
    org_id: int,
    user_id: int,
    req: OrgMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager")),
) -> dict:
    """修改成员角色（仅admin/general_manager可操作）"""
    member = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id,
        OrganizationMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="该用户不是组织成员")

    member.role_in_org = req.role_in_org

    # 同步更新 User 表的 is_org_admin
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_org_admin = (req.role_in_org == "admin")

    db.commit()
    db.refresh(member)
    return _enrich_member_out(member, db)


# ═══════════════════ 当前用户组织信息 ═══════════════════


@auth_router.get("/my-org", response_model=Optional[MyOrgOut])
def get_my_org(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前用户所属组织信息"""
    org_id = current_user.org_id
    if not org_id:
        return None

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        return None

    # 查询当前用户在组织中的成员信息
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id,
        OrganizationMember.user_id == current_user.id,
    ).first()

    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id
    ).count()

    return MyOrgOut(
        id=org.id,
        name=org.name,
        code=org.code,
        contact_email=org.contact_email,
        phone=org.phone,
        address=org.address,
        is_active=org.is_active,
        max_users=org.max_users,
        member_count=member_count,
        is_org_admin=current_user.is_org_admin or False,
        role_in_org=membership.role_in_org if membership else None,
        created_at=org.created_at,
    )


# ═══════════════════ 辅助函数 ═══════════════════


def _enrich_org_out(org: Organization, db: Session) -> OrgOut:
    """将 Organization 模型扩展为 OrgOut（含 member_count）"""
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org.id
    ).count()
    return OrgOut(
        id=org.id,
        name=org.name,
        code=org.code,
        contact_email=org.contact_email,
        phone=org.phone,
        address=org.address,
        is_active=org.is_active,
        max_users=org.max_users,
        member_count=member_count,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def _enrich_member_out(member: OrganizationMember, db: Session) -> OrgMemberOut:
    """将 OrganizationMember 模型扩展为 OrgMemberOut（含用户信息）"""
    user = db.query(User).filter(User.id == member.user_id).first()
    return OrgMemberOut(
        id=member.id,
        org_id=member.org_id,
        user_id=member.user_id,
        role_in_org=member.role_in_org,
        username=user.username if user else "",
        full_name=user.full_name if user else None,
        email=user.email if user else None,
        joined_at=member.joined_at,
    )
