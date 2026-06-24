"""可制造性分析(DFM)模块 — 数据模型

包含: DFMChecklist, DFMReport, DFMReportItem, DFMScoreWeight
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ItemStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    VERIFIED = "verified"


class DfmCategory(str, enum.Enum):
    STRUCTURAL = "structural"       # 结构DFM
    PROCESS = "process"             # 工艺DFM
    ASSEMBLY = "assembly"           # 装配DFM
    ELECTRICAL = "electrical"       # 电气DFM
    MOLD = "mold"                   # 模具DFM


# ── ① DFM检查项模板 ──

class DFMChecklist(Base):
    """可制造性检查项模板"""
    __tablename__ = "dfm_checklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_code = Column(String(100), nullable=False, index=True, comment="检查项编码")
    item_name = Column(String(300), nullable=False, comment="检查项名称")
    description = Column(Text, nullable=True, comment="检查项描述")
    dfm_category = Column(String(50), nullable=False, default="structural", comment="分类: structural/process/assembly/electrical/mold")
    severity = Column(String(20), nullable=False, default="major", comment="严重等级: critical/major/minor")
    applicable_product_types = Column(String(500), nullable=True, comment="适用产品类型（逗号分隔）")
    reference_standard = Column(String(300), nullable=True, comment="参考标准")
    check_method = Column(Text, nullable=True, comment="检查方法描述")
    weight = Column(Float, nullable=True, default=1.0, comment="权重系数")
    sort_order = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="active")
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── ② DFM分析报告 ──

class DFMReport(Base):
    """DFM分析报告"""
    __tablename__ = "dfm_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_no = Column(String(50), nullable=False, unique=True, comment="报告编号")
    title = Column(String(300), nullable=False, comment="报告标题")
    project_id = Column(Integer, nullable=True, comment="关联项目ID")
    prototype_id = Column(Integer, nullable=True, comment="关联样机ID")
    product_type = Column(String(100), nullable=True, comment="产品类型")
    version = Column(String(50), nullable=True, default="V1.0")
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft/in_progress/completed")
    total_score = Column(Float, nullable=True, comment="总分0-100")
    summary = Column(Text, nullable=True, comment="总结和建议")
    created_by = Column(String(100), nullable=True)
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("DFMReportItem", back_populates="report",
                          cascade="all, delete-orphan", passive_deletes=True,
                          order_by="DFMReportItem.sort_order")


# ── ③ 报告问题项 ──

class DFMReportItem(Base):
    """DFM报告问题项"""
    __tablename__ = "dfm_report_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("dfm_reports.id", ondelete="CASCADE"), nullable=False)
    checklist_id = Column(Integer, nullable=True, comment="关联检查项ID（可选，自定义问题可为空）")
    issue_desc = Column(Text, nullable=False, comment="问题描述")
    dfm_category = Column(String(50), nullable=True, comment="分类")
    severity = Column(String(20), nullable=False, default="major", comment="严重等级")
    suggestion = Column(Text, nullable=True, comment="建议方案")
    responsible_person = Column(String(100), nullable=True, comment="责任人")
    status = Column(String(20), nullable=False, default="pending", comment="状态: pending/resolved/verified")
    score = Column(Float, nullable=True, comment="项得分0-100")
    attachments = Column(JSON, nullable=True)
    sort_order = Column(Integer, default=0)
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report = relationship("DFMReport", back_populates="items")


# ── ④ 评分权重配置 ──

class DFMScoreWeight(Base):
    """DFM评分权重配置（按产品类型）"""
    __tablename__ = "dfm_score_weights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_type = Column(String(100), nullable=False, comment="产品类型，如 split_ac/portable_ac/dehumidifier")
    dfm_category = Column(String(50), nullable=False, comment="分类")
    weight = Column(Float, nullable=False, default=0.2, comment="权重0-1，同一产品类型下权重和=1")
    org_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
