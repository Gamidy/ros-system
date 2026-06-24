"""多租户组织模型

Organization: 租户组织表
OrganizationMember: 组织成员关联表（成员角色）
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Organization(Base):
    """租户组织 — 共享数据库 + 行级 org_id 隔离的核心实体"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="组织名称")
    code = Column(String(50), unique=True, index=True, nullable=False, comment="组织编码（唯一标识）")
    contact_email = Column(String(100), nullable=True, comment="联系邮箱")
    phone = Column(String(20), nullable=True, comment="联系电话")
    address = Column(String(500), nullable=True, comment="地址")
    is_active = Column(Boolean, default=True, comment="是否启用")
    max_users = Column(Integer, default=100, comment="最大用户数限制")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", foreign_keys="User.org_id")


class OrganizationMember(Base):
    """组织成员关联表 — 记录用户在组织中的角色"""
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, comment="组织ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    role_in_org = Column(String(20), default="member", comment="组织内角色: admin/member")
    joined_at = Column(DateTime, server_default=func.now(), comment="加入时间")

    # 关联
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="org_membership", foreign_keys=[user_id])
