"""用户与角色模型"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
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

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(50), default="engineer")  # 13种角色，自注册默认 engineer
    department = Column(String(50), nullable=True)
    position = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)
    application_reason = Column(String(500), nullable=True)
    application_status = Column(String(20), default="approved")  # pending/approved/rejected
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
