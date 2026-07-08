"""Phase 6 S2 — 认证中心核心模型

包含：CertificationRequirement, CertificationProject, CertificationSample,
CertificationExecution, CertificationResult, Certificate, CertificateVersion

实体1-7 — 架构师批准设计
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums_s2 import (
    CertRequirementSource,
    CertProjectStatus,
    CertResultStatus,
    CertSampleStatus,
    CertExecutionStatus,
    CertificateStatus,
    CertType,
)


class CertificationRequirement(Base):
    """认证需求 — 从TargetMarket自动生成，**禁止人工创建**"""
    __tablename__ = "certification_requirements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, comment="关联项目")
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=False, comment="关联目标市场")
    cert_type = Column(String(20), nullable=False, comment=f"认证类型: {[e.value for e in CertType]}")
    cert_body = Column(String(100), nullable=True, comment="认证机构")
    is_mandatory = Column(Boolean, default=True, comment="是否强制")
    status = Column(String(20), nullable=False, default=CertExecutionStatus.PENDING.value,
                    comment=f"状态: {[e.value for e in CertExecutionStatus]}")
    source_type = Column(String(20), nullable=False, default=CertRequirementSource.TARGET_MARKET.value,
                         comment="来源类型: 固定为target_market")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    project = relationship("Project")
    target_market = relationship("TargetMarket")


class CertificationProject(Base):
    """认证项目 — Project × TargetMarket 组合，例如 KFR-35GW → EU"""
    __tablename__ = "certification_projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="认证项目编号: CP-YYYYMMDD-XXXX")
    name = Column(String(200), nullable=False, comment="认证项目名称")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, comment="关联项目")
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=False, comment="关联目标市场")
    cert_types = Column(Text, nullable=True, comment="认证类型JSON数组")
    status = Column(String(20), nullable=False, default=CertProjectStatus.PLANNING.value,
                    comment=f"状态: {[e.value for e in CertProjectStatus]}")
    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    remark = Column(Text, nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    project = relationship("Project")
    target_market = relationship("TargetMarket")
    samples = relationship("CertificationSample", back_populates="cert_project",
                           cascade="all, delete-orphan")


class CertificationSample(Base):
    """认证样机 — 强制关联Prototype（不是 Project）"""
    __tablename__ = "certification_samples"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cert_project_id = Column(Integer, ForeignKey("certification_projects.id"), nullable=False, comment="关联认证项目")
    prototype_id = Column(Integer, ForeignKey("prototypes.id"), nullable=False, comment="强制关联Prototype")
    cert_type = Column(String(20), nullable=False, comment=f"认证类型: {[e.value for e in CertType]}")
    sample_no = Column(String(50), unique=True, index=True, nullable=False, comment="样机编号(唯一)")
    status = Column(String(20), nullable=False, default=CertSampleStatus.PENDING.value,
                    comment=f"状态: {[e.value for e in CertSampleStatus]}")
    submitted_date = Column(Date, nullable=True)
    remark = Column(Text, nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    cert_project = relationship("CertificationProject", back_populates="samples")
    prototype = relationship("Prototype")
    executions = relationship("CertificationExecution", back_populates="cert_sample",
                              cascade="all, delete-orphan")


class CertificationExecution(Base):
    """认证执行"""
    __tablename__ = "certification_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cert_sample_id = Column(Integer, ForeignKey("certification_samples.id"), nullable=False, comment="关联认证样机")
    lab = Column(String(100), nullable=True, comment="实验室")
    agency = Column(String(100), nullable=True, comment="代理机构")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default=CertExecutionStatus.PENDING.value,
                    comment=f"状态: {[e.value for e in CertExecutionStatus]}")
    result_summary = Column(Text, nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    cert_sample = relationship("CertificationSample", back_populates="executions")
    results = relationship("CertificationResult", back_populates="cert_execution",
                           cascade="all, delete-orphan")


class CertificationResult(Base):
    """认证结果 — 状态机: DRAFT → SUBMITTED → TESTING → PASSED/FAILED → EXPIRED"""
    __tablename__ = "certification_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cert_execution_id = Column(Integer, ForeignKey("certification_executions.id"), nullable=False, comment="关联认证执行")
    status = Column(String(20), nullable=False, default=CertResultStatus.DRAFT.value,
                    comment=f"状态: {[e.value for e in CertResultStatus]}")
    result_date = Column(Date, nullable=True)
    summary = Column(Text, nullable=True)
    attachments = Column(Text, nullable=True, comment="附件JSON")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    cert_execution = relationship("CertificationExecution", back_populates="results")
    certificates = relationship("Certificate", back_populates="cert_result",
                                cascade="all, delete-orphan")


class Certificate(Base):
    """证书"""
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cert_result_id = Column(Integer, ForeignKey("certification_results.id"), nullable=False, comment="关联认证结果")
    cert_no = Column(String(100), unique=True, index=True, nullable=False, comment="证书编号(唯一)")
    cert_type = Column(String(20), nullable=False, comment=f"认证类型: {[e.value for e in CertType]}")
    issuing_body = Column(String(100), nullable=True, comment="发证机构")
    issue_date = Column(Date, nullable=False, comment="发证日期")
    expiry_date = Column(Date, nullable=True, comment="到期日期")
    status = Column(String(20), nullable=False, default=CertificateStatus.ACTIVE.value,
                    comment=f"状态: {[e.value for e in CertificateStatus]}")
    attachments = Column(Text, nullable=True, comment="附件JSON")
    remark = Column(Text, nullable=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    cert_result = relationship("CertificationResult", back_populates="certificates")
    versions = relationship("CertificateVersion", back_populates="certificate",
                            cascade="all, delete-orphan")


class CertificateVersion(Base):
    """证书版本 — 架构师要求新增，如压缩机变更→重新认证"""
    __tablename__ = "certificate_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    certificate_id = Column(Integer, ForeignKey("certificates.id"), nullable=False, comment="关联证书")
    version_no = Column(String(10), nullable=False, comment="版本号: V1/V2/V3")
    cert_no = Column(String(100), nullable=False, comment="证书编号(当前版本对应的证书号)")
    issuing_body = Column(String(100), nullable=True, comment="发证机构")
    issue_date = Column(Date, nullable=False, comment="发证日期")
    expiry_date = Column(Date, nullable=True, comment="到期日期")
    status = Column(String(20), nullable=False, default="active", comment="active/superseded/expired")
    change_reason = Column(Text, nullable=True, comment="变更原因，如'压缩机变更→重新认证'")
    attachments = Column(Text, nullable=True, comment="附件JSON")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    certificate = relationship("Certificate", back_populates="versions")
