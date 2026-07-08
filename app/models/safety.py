"""安规管理模块 — 数据模型

包含: SafetyStandard, SafetyInspectionItem,
       SupplierSafetyQualification, SupplierSafetyAuditRecord
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class StandardStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    OBSOLETE = "obsolete"


class InspectionCategory(str, enum.Enum):
    ELECTRICAL = "electrical"       # 电气安全
    MECHANICAL = "mechanical"       # 机械安全
    FIRE = "fire"                   # 防火
    EMC = "emc"                     # EMC
    CHEMICAL = "chemical"           # 化学/环保
    OTHER = "other"                 # 其他


class QualStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuditResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


# ── ① 安全标准库 ──

class SafetyStandard(Base):
    """安全标准库 — 各国空调相关安全标准"""
    __tablename__ = "safety_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_code = Column(String(100), nullable=False, index=True, comment="标准编号，如 IEC 60335-2-40")
    standard_name_cn = Column(String(300), nullable=False, comment="标准中文名称")
    standard_name_en = Column(String(300), nullable=True, comment="标准英文名称")
    issuing_body = Column(String(200), nullable=True, comment="发布机构，如 IEC/UL/GB")
    applicable_market = Column(String(200), nullable=True, comment="适用市场/国家")
    standard_type = Column(String(50), nullable=False, default="safety", comment="标准类型：safety/energy/emc/environmental")
    version = Column(String(50), nullable=True, default="V1.0", comment="标准版本号")
    publish_date = Column(Date, nullable=True, comment="发布日期")
    effective_date = Column(Date, nullable=True, comment="生效日期")
    abolish_date = Column(Date, nullable=True, comment="废止日期")
    summary = Column(Text, nullable=True, comment="标准摘要说明")
    attachment_url = Column(String(500), nullable=True, comment="标准文件附件URL")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/draft/obsolete")
    org_id = Column(Integer, nullable=True, comment="多租户组织ID")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    inspection_items = relationship("SafetyInspectionItem", back_populates="standard",
                                     cascade="all, delete-orphan", passive_deletes=True)


# ── ② 安规检测项 ──

class SafetyInspectionItem(Base):
    """安规检测项 — 安全标准的具体检测参数"""
    __tablename__ = "safety_inspection_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_id = Column(Integer, ForeignKey("safety_standards.id", ondelete="CASCADE"), nullable=False, comment="所属安全标准ID")
    item_code = Column(String(100), nullable=False, comment="检测项编码")
    item_name = Column(String(300), nullable=False, comment="检测项名称")
    inspection_category = Column(String(50), nullable=True, comment="检测类别：electrical/mechanical/fire/emc/chemical/other")
    param_name = Column(String(200), nullable=True, comment="检测参数名")
    standard_value_min = Column(Float, nullable=True, comment="标准值下限")
    standard_value_max = Column(Float, nullable=True, comment="标准值上限")
    standard_value_nominal = Column(String(100), nullable=True, comment="标准标称值（文本描述，如 220V±10%）")
    unit = Column(String(50), nullable=True, comment="单位")
    applicable_product_type = Column(String(200), nullable=True, comment="适用产品类别")
    test_method = Column(Text, nullable=True, comment="检测方法描述")
    reference_clause = Column(String(100), nullable=True, comment="参考标准条款编号")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/inactive")
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    standard = relationship("SafetyStandard", back_populates="inspection_items")


# ── ③ 供应商安规资质 ──

class SupplierSafetyQualification(Base):
    """供应商安规资质"""
    __tablename__ = "supplier_safety_qualifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, nullable=False, comment="供应商ID (FK→suppliers.id)")
    qualification_type = Column(String(100), nullable=False, comment="资质类型：ISO9001/UL/CCC/CE等")
    cert_no = Column(String(200), nullable=True, comment="证书编号")
    issuing_body = Column(String(200), nullable=True, comment="发证机构")
    issue_date = Column(Date, nullable=True, comment="发证日期")
    expiry_date = Column(Date, nullable=True, comment="有效期至")
    attachments = Column(JSON, nullable=True, comment="附件（JSON数组）")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/expired/revoked")
    audit_status = Column(String(20), nullable=False, default="pending", comment="审核状态: pending/approved/rejected")
    audit_comment = Column(Text, nullable=True, comment="审核意见")
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    audit_records = relationship("SupplierSafetyAuditRecord", back_populates="qualification",
                                  cascade="all, delete-orphan", passive_deletes=True)


class SupplierSafetyAuditRecord(Base):
    """供应商安规审核记录"""
    __tablename__ = "supplier_safety_audit_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    qualification_id = Column(Integer, ForeignKey("supplier_safety_qualifications.id", ondelete="CASCADE"), nullable=False)
    audit_date = Column(Date, nullable=False, comment="审核日期")
    auditor = Column(String(100), nullable=True, comment="审核人")
    result = Column(String(20), nullable=False, default="pass", comment="结果: pass/fail/conditional")
    findings = Column(JSON, nullable=True, comment="发现项（JSON数组）")
    attachments = Column(JSON, nullable=True, comment="附件")
    next_audit_date = Column(Date, nullable=True, comment="下次审核日期")
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    qualification = relationship("SupplierSafetyQualification", back_populates="audit_records")
