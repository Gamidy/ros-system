"""用户与角色模型"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default="engineer")  # admin | manager | engineer | certifier
    department = Column(String(50), nullable=True)
    position = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)
    application_reason = Column(String(500), nullable=True)
    application_status = Column(String(20), default="approved")  # pending/approved/rejected
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
