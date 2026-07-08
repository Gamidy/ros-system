"""Phase 6 S2 — 认证门禁规则模型

实体8 — 架构师批准设计
不是硬编码 M6 → CE，必须可配置
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import GateCode
from app.core.enums_s2 import CertType


class CertificationGateRule(Base):
    """认证门禁规则 — 可配置的 Gate × 认证类型映射"""
    __tablename__ = "certification_gate_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    name = Column(String(100), nullable=False, comment="规则名称")
    gate_code = Column(String(10), nullable=False, comment=f"门禁编号: {[e.value for e in GateCode]}")
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=True, comment="目标市场(nullable=通配)")
    cert_type = Column(String(20), nullable=False, comment=f"认证类型: {[e.value for e in CertType]}")
    is_required = Column(Boolean, default=True, comment="是否必需")
    auto_block = Column(Boolean, default=False, comment="不符合时自动阻塞Gate")
    priority = Column(Integer, default=100, comment="优先级(越小越优先)")
    status = Column(String(20), nullable=False, default="active", comment="active/inactive")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    # 关系
    target_market = relationship("TargetMarket")
