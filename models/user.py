"""用户与角色模型"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.permissions import ALL_ROLES


class UserRole:
    """用户角色常量 — 与 permissions 模块保持同步"""
    ADMIN = "admin"
    GENERAL_MANAGER = "general_manager"
    RD_DIRECTOR = "rd_director"
    PRODUCT_MANAGER = "product_manager"
    SYSTEMS_ENGINEER = "systems_engineer"
    STRUCTURAL_ENGINEER = "structural_engineer"
    ELECTRICAL_CONTROL_ENGINEER = "electrical_control_engineer"
    ELECTRICAL_ENGINEER = "electrical_engineer"
    PROCUREMENT = "procurement"
    QUALITY_ENGINEER = "quality_engineer"
    PROCESS_ENGINEER = "process_engineer"
    PROJECT_ADMIN = "project_admin"
    PRODUCTION = "production"
    ENGINEER = "engineer"  # 向后兼容：原系统默认角色

    ALL = ALL_ROLES  # 所有有效角色的列表

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.ALL


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    username = Column(String(50), unique=True, index=True, nullable=False,  # username)
    email = Column(String(100), unique=True, nullable=True,  # email)
    hashed_password = Column(String(255), nullable=False,  # hashed_password)
    full_name = Column(String(100), nullable=True,  # full_name)
    role = Column(String(50), default="engineer")  # 13种角色，自注册默认 engineer
    department = Column(String(50), nullable=True,  # department)
    position = Column(String(50), nullable=True,  # position)
    phone = Column(String(20), nullable=True,  # phone)
    application_reason = Column(String(500), nullable=True,  # application_reason)
    application_status = Column(String(20), default="approved")  # pending/approved/rejected
    is_active = Column(Boolean, default=True,  # is_active)
    # ---- 多租户字段 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    is_org_admin = Column(Boolean, default=False, comment="是否为组织管理员")
    # ---- 时间戳 ----
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    # 多租户关联
    organization = relationship("Organization", back_populates="users", foreign_keys=[org_id])
    org_membership = relationship("OrganizationMember", back_populates="user", foreign_keys="OrganizationMember.user_id")
