"""Phase 6 S2 — 变更影响模型

包含：ChangeImpactRule, ChangeImpactRecord

实体9-10 — 架构师批准设计
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums_s2 import ImpactLevel


class ChangeImpactRule(Base):
    """变更影响规则 — 如"压缩机变更→影响CE/CB\""""
    __tablename__ = "change_impact_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称: 如'压缩机变更→影响CE/CB'")
    description = Column(Text, nullable=True)
    trigger_type = Column(String(30), nullable=False, comment="触发类型: part_category/material_type/cdf_type/market_change")
    trigger_value = Column(String(100), nullable=False, comment="触发值: 如 compressor/safety_part/cdf_item")
    affected_cert_types = Column(Text, nullable=False, comment="影响的认证类型JSON数组: [\"CE\",\"CB\"]")
    impact_level = Column(String(20), nullable=False, comment=f"影响等级: {[e.value for e in ImpactLevel]}")
    is_active = Column(Boolean, default=True, comment="是否启用")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    impact_records = relationship("ChangeImpactRecord", back_populates="matched_rule",
                                  cascade="all, delete-orphan")


class ChangeImpactRecord(Base):
    """变更影响日志 — 变更触发的认证影响分析记录"""
    __tablename__ = "change_impact_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ecr_id = Column(Integer, nullable=True, comment="预留ECR关联ID")
    prototype_id = Column(Integer, ForeignKey("prototypes.id"), nullable=True, comment="关联样机（ECR/ECO触发时可空）")
    changed_part = Column(String(200), nullable=True, comment="变更部件描述")
    matched_rule_id = Column(Integer, ForeignKey("change_impact_rules.id"), nullable=True, comment="匹配的规则ID")
    impact_level = Column(String(20), nullable=False, comment=f"影响等级: {[e.value for e in ImpactLevel]}")
    affected_cert_types = Column(Text, nullable=False, comment="受影响的认证类型JSON")
    analysis_detail = Column(Text, nullable=True, comment="分析详情")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    prototype = relationship("Prototype")
    matched_rule = relationship("ChangeImpactRule", back_populates="impact_records")
