"""Verification Requirement（验证需求）模型

数字主线入口：ProductPlan → VR → Project → Prototype → TestCenter
支持来源追踪：ProductPlan / Customer / Standard / Certification / Gate
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import (
    VerificationRequirementCategory,
    VerificationRequirementSource,
    VerificationRequirementStatus,
)


class VerificationRequirement(Base):
    """验证需求 — S1核心实体"""
    __tablename__ = "verification_requirements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vr_code = Column(String(50), unique=True, index=True, nullable=False, comment="VR编号: VR-20260624-0001")

    # 基本描述
    title = Column(String(200), nullable=False, comment="标题: 如 APF ≥ 5.20")
    category = Column(String(30), nullable=False, comment=f"分类: {[e.value for e in VerificationRequirementCategory]}")
    target_value = Column(String(100), nullable=True, comment="目标值: 如 ≥5.20")
    unit = Column(String(30), nullable=True, comment="单位: 如 W/W, dB")

    # ★ 来源追踪（架构师要求）
    source_type = Column(String(30), nullable=False, comment=f"来源类型: {[e.value for e in VerificationRequirementSource]}")
    source_id = Column(String(100), nullable=True, comment="来源ID/引用: ProductPlan.id, 客户要求编号等")
    source_detail = Column(Text, nullable=True, comment="来源详细信息JSON")

    # 关联
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, comment="关联项目")
    product_plan_id = Column(Integer, ForeignKey("product_plans.id"), nullable=True, comment="关联产品策划")
    gate_code = Column(String(10), nullable=True, comment="关联Gate: M4/M5/M6")

    # 状态
    status = Column(String(20), nullable=False, default=VerificationRequirementStatus.PENDING.value,
                    comment=f"状态: {[e.value for e in VerificationRequirementStatus]}")
    remark = Column(Text, nullable=True)

    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    project = relationship("Project", back_populates="verification_requirements")
    test_requests = relationship("TestRequest", back_populates="verification_requirement",
                                 foreign_keys="TestRequest.vr_id")
