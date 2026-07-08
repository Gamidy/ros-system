"""TargetMarket（目标市场）模型 — 市场驱动的实验和认证配置

设计：TargetMarket → RequiredTest + RequiredCertification + RequiredStandard
不绑定CCC — 只在 target_market=CN 时出现

架构师要求：
EU → CE → EN14825
US → UL → AHRI
AU → SAA
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import TargetMarketCode, CertType, VerificationRequirementCategory


class TargetMarket(Base):
    """目标市场"""
    __tablename__ = "target_markets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    market_code = Column(String(10), unique=True, nullable=False, comment=f"市场代码: {[e.value for e in TargetMarketCode]}")
    market_name = Column(String(100), nullable=False, comment="市场名称")
    description = Column(Text, nullable=True,  # description)

    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")

    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    # 关系
    required_tests = relationship("RequiredTest", back_populates="target_market", cascade="all, delete-orphan")
    required_certifications = relationship("RequiredCertification", back_populates="target_market", cascade="all, delete-orphan")
    required_standards = relationship("RequiredStandard", back_populates="target_market", cascade="all, delete-orphan")


class RequiredTest(Base):
    """目标市场要求的测试项"""
    __tablename__ = "required_tests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=False, comment="关联市场")
    test_category = Column(String(30), nullable=False, comment=f"实验分类: {[e.value for e in VerificationRequirementCategory]}")
    standard = Column(String(100), nullable=True, comment="测试标准: 如 EN 14511")
    is_required = Column(Boolean, default=True, comment="是否强制")
    sort_order = Column(Integer, default=0, comment="排序")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    target_market = relationship("TargetMarket", back_populates="required_tests")


class RequiredCertification(Base):
    """目标市场要求的认证项"""
    __tablename__ = "required_certifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=False, comment="关联市场")
    cert_type = Column(String(20), nullable=False, comment=f"认证类型: {[e.value for e in CertType]}")
    cert_body = Column(String(100), nullable=True, comment="认证机构")
    is_mandatory = Column(Boolean, default=True, comment="是否强制")
    sort_order = Column(Integer, default=0, comment="排序")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    target_market = relationship("TargetMarket", back_populates="required_certifications")


class RequiredStandard(Base):
    """目标市场要求的标准"""
    __tablename__ = "required_standards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=False, comment="关联市场")
    standard_code = Column(String(50), nullable=False, comment="标准编号: EN 14825, AHRI 210/240")
    standard_name = Column(String(200), nullable=True, comment="标准名称")
    is_core = Column(Boolean, default=True, comment="是否核心标准")
    sort_order = Column(Integer, default=0, comment="排序")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    target_market = relationship("TargetMarket", back_populates="required_standards")
