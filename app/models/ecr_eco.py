"""Phase 6 S3 — ECR/ECO 工程变更控制模型

ECR = Engineering Change Request（工程变更申请）
ECO = Engineering Change Order（工程变更指令）

状态机:
  ECR: DRAFT → SUBMITTED → REVIEWING → APPROVED/REJECTED → CONVERTED
  ECO: DRAFT → IMPLEMENTING → VERIFIED → EFFECTIVE → CLOSED/CANCELLED

审批流: 复用 ApprovalRequest(request_type='ecr')
BOM联动: ECO EFFECTIVE → eco_bom_service.on_eco_effective()
S2集成: ChangeImpactRecord.ecr_id → ECR关联
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    ECRStatus, ECOStatus, ECRType, ECRUrgency,
    ECOChangeType, ECOObjectType,
)


class ECRAttachment(Base):
    """ECR附件"""
    __tablename__ = "ecr_attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ecr_id = Column(Integer, ForeignKey("ecr_requests.id"), nullable=False, comment="关联ECR")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    file_type = Column(String(50), nullable=True, comment="文件类型")
    file_size = Column(Integer, default=0, comment="文件大小(字节)")
    uploaded_by = Column(String(100), nullable=True, comment="上传人")
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    ecr = relationship("ECRRequest", back_populates="attachments")


class ECRRequest(Base):
    """工程变更申请"""
    __tablename__ = "ecr_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="ECR编号: ECR-YYYYMMDD-XXXX")
    title = Column(String(200), nullable=False, comment="变更标题")
    ecr_type = Column(String(30), nullable=False, default=ECRType.OTHER.value,
                      comment=f"变更类型: {[e.value for e in ECRType]}")
    reason = Column(Text, nullable=False, comment="变更原因")
    urgency = Column(String(20), nullable=False, default=ECRUrgency.MEDIUM.value,
                     comment=f"紧急度: {[e.value for e in ECRUrgency]}")
    affected_products = Column(JSON, nullable=True, comment="影响产品JSON")
    affected_documents = Column(JSON, nullable=True, comment="影响文件JSON")
    description = Column(Text, nullable=True, comment="详细描述")
    status = Column(String(20), nullable=False, default=ECRStatus.DRAFT.value,
                    comment=f"状态: {[e.value for e in ECRStatus]}")
    workflow_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True, comment="关联审批请求ID")
    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="提交人")
    submitter_name = Column(String(50), nullable=True, comment="提交人姓名")
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="审批人")
    reviewed_at = Column(DateTime, nullable=True, comment="审批时间")
    rejection_reason = Column(Text, nullable=True, comment="驳回原因")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    submitter = relationship("User", foreign_keys=[submitter_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    attachments = relationship("ECRAttachment", back_populates="ecr", cascade="all, delete-orphan")
    eco = relationship("ECO", back_populates="ecr", uselist=False)


class ECO(Base):
    """工程变更指令"""
    __tablename__ = "ecos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="ECO编号: ECO-YYYYMMDD-XXXX")
    ecr_id = Column(Integer, ForeignKey("ecr_requests.id"), nullable=True, comment="来源ECR")
    title = Column(String(200), nullable=False, comment="变更标题")
    change_summary = Column(Text, nullable=False, comment="变更摘要")
    implementation_plan = Column(Text, nullable=True, comment="实施方案")
    effective_date = Column(Date, nullable=True, comment="生效日期")
    status = Column(String(20), nullable=False, default=ECOStatus.DRAFT.value,
                    comment=f"状态: {[e.value for e in ECOStatus]}")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人")
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="验证人")
    verified_at = Column(DateTime, nullable=True, comment="验证时间")
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="关闭人")
    closed_at = Column(DateTime, nullable=True, comment="关闭时间")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    ecr = relationship("ECRRequest", back_populates="eco")
    items = relationship("ECOItem", back_populates="eco", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    verifier = relationship("User", foreign_keys=[verified_by])


class ECOItem(Base):
    """ECO明细项"""
    __tablename__ = "eco_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    eco_id = Column(Integer, ForeignKey("ecos.id"), nullable=False, comment="关联ECO")
    seq = Column(Integer, nullable=False, default=0, comment="序号")
    change_type = Column(String(20), nullable=False,
                         comment=f"变更类型: {[e.value for e in ECOChangeType]}")
    object_type = Column(String(20), nullable=False,
                         comment=f"对象类型: {[e.value for e in ECOObjectType]}")
    object_id = Column(Integer, nullable=True, comment="对象ID")
    object_code = Column(String(100), nullable=True, comment="对象编码")
    object_name = Column(String(200), nullable=True, comment="对象名称")
    old_value = Column(Text, nullable=True, comment="原值")
    new_value = Column(Text, nullable=True, comment="新值")
    description = Column(Text, nullable=True, comment="描述")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    eco = relationship("ECO", back_populates="items")
