"""审计日志模型"""
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.core.database import Base


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    username = Column(String(50), nullable=False, comment="用户名")
    role = Column(String(50), nullable=False, comment="角色")
    method = Column(String(10), nullable=False, comment="HTTP方法: GET/POST/PUT/PATCH/DELETE")
    path = Column(String(200), nullable=False, comment="请求路径")
    status_code = Column(Integer, nullable=False, comment="HTTP状态码")

    # 增强字段
    action_type = Column(String(20), nullable=True, comment="操作类型: create/update/delete/view/other")
    resource_type = Column(String(50), nullable=True, comment="资源类型: project/bom/ecr/product/...")
    resource_id = Column(Integer, nullable=True, comment="资源ID")
    detail = Column(Text, nullable=True, comment="操作描述/摘要")
    request_body = Column(Text, nullable=True, comment="请求体(敏感字段过滤后,≤1KB)")

    ip_address = Column(String(45), nullable=True, comment="客户端IP")
    user_agent = Column(String(255), nullable=True, comment="User-Agent")
    duration_ms = Column(Integer, default=0, comment="请求耗时(毫秒)")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
