"""审计日志模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    role = Column(String(50), nullable=False)
    method = Column(String(10), nullable=False)  # GET/POST/PATCH/DELETE
    path = Column(String(200), nullable=False)
    status_code = Column(Integer, nullable=False)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
