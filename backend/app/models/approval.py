"""审批流模型: ApprovalChain → ApprovalStep + ApprovalRequest + ApprovalRecord"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApprovalChain(Base):
    """审批链定义"""
    __tablename__ = "approval_chains"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="审批链名称")
    code = Column(String(50), unique=True, index=True, nullable=False, comment="审批链编码")
    description = Column(Text, nullable=True, comment="描述")
    steps = Column(JSON, nullable=True, comment="步骤定义（兼容JSON格式）")
    created_at = Column(DateTime, server_default=func.now())

    step_items = relationship("ApprovalStep", back_populates="chain",
                              order_by="ApprovalStep.seq",
                              cascade="all, delete-orphan")


class ApprovalStep(Base):
    """审批步骤"""
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chain_id = Column(Integer, ForeignKey("approval_chains.id", ondelete="CASCADE"), nullable=False)
    seq = Column(Integer, nullable=False, comment="步骤序号")
    role = Column(String(50), nullable=False, comment="审批角色: admin/研发总监/模块经理/总经理/采购/工程师/个人")
    name = Column(String(100), nullable=False, comment="步骤名称")
    created_at = Column(DateTime, server_default=func.now())

    chain = relationship("ApprovalChain", back_populates="step_items")


class ApprovalRequest(Base):
    """审批请求"""
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chain_id = Column(Integer, ForeignKey("approval_chains.id"), nullable=False)
    request_type = Column(String(50), nullable=False, comment="请求类型: ecr/purchase/register")
    request_id = Column(Integer, nullable=True, comment="关联业务记录ID")
    title = Column(String(200), nullable=False, comment="审批标题")
    requester = Column(String(100), nullable=False, comment="申请人")
    status = Column(String(20), default="pending", comment="pending/approved/rejected")
    current_step = Column(Integer, default=1, comment="当前步骤序号")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    records = relationship("ApprovalRecord", back_populates="request",
                           cascade="all, delete-orphan")


class ApprovalRecord(Base):
    """审批记录"""
    __tablename__ = "approval_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(Integer, ForeignKey("approval_steps.id"), nullable=True)
    approver = Column(String(100), nullable=False, comment="审批人")
    decision = Column(String(20), nullable=False, comment="approved/rejected")
    comment = Column(Text, nullable=True, comment="审批意见")
    decided_at = Column(DateTime, server_default=func.now())

    request = relationship("ApprovalRequest", back_populates="records")
