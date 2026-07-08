"""外协管理模块 — 数据模型

包含: OutsourcePartner, OutsourceOrder, OutsourceOrderItem,
       OutsourceQualityRecord, OutsourceQualityFile
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PartnerType(str, enum.Enum):
    MOLD = "mold"                 # 模具外协
    ELECTRICAL = "electrical"     # 电控外协
    SYSTEM = "system"             # 系统外协
    STRUCTURAL = "structural"     # 结构外协
    OTHER = "other"               # 其他


class QualityResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


# ── ① 外协厂商 ──

class OutsourcePartner(Base):
    """外协厂商信息"""
    __tablename__ = "outsource_partners"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    code = Column(String(50), unique=True, nullable=False, comment="厂商编码")
    name = Column(String(200), nullable=False, comment="厂商名称")
    partner_type = Column(String(50), nullable=False, default="other", comment="外协类型: mold/electrical/system/structural/other")
    contact_person = Column(String(100), nullable=True,  # contact_person)
    contact_phone = Column(String(50), nullable=True,  # contact_phone)
    address = Column(String(500), nullable=True,  # address)
    business_scope = Column(String(500), nullable=True, comment="业务范围")
    qualification_level = Column(String(20), default="B", comment="资质等级: A/B/C")
    rating = Column(Integer, nullable=True, comment="综合评分0-100")
    status = Column(String(20), default="active",  # status)
    remark = Column(Text, nullable=True,  # remark)
    org_id = Column(Integer, nullable=True,  # org_id)
    created_at = Column(DateTime, default=datetime.utcnow,  # created_at)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,  # updated_at)

    orders = relationship("OutsourceOrder", back_populates="partner",
                           cascade="all, delete-orphan", passive_deletes=True)


# ── ② 外协订单 ──

class OutsourceOrder(Base):
    """外协加工订单"""
    __tablename__ = "outsource_orders"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    order_no = Column(String(50), unique=True, nullable=False, comment="订单号 OS-YYYYMMDD-XXXX")
    partner_id = Column(Integer, ForeignKey("outsource_partners.id", ondelete="CASCADE"), nullable=False,  # partner_id)
    project_id = Column(Integer, nullable=True, comment="关联项目ID")
    title = Column(String(300), nullable=False, comment="订单标题")
    order_type = Column(String(50), nullable=False, comment="订单类型: mold/part/assembly/other")
    quantity = Column(Integer, default=1, comment="数量")
    unit = Column(String(20), default="批", comment="单位")
    unit_price = Column(Float, default=0.0, comment="单价")
    total_amount = Column(Float, default=0.0, comment="总金额")
    delivery_date = Column(Date, nullable=True, comment="要求交期")
    actual_delivery_date = Column(Date, nullable=True, comment="实际交期")
    status = Column(String(20), nullable=False, default="draft",  # status
                    comment="draft/pending/in_progress/delivered/closed/cancelled")
    priority = Column(String(20), default="normal", comment="priority: low/normal/high/urgent")
    technical_requirements = Column(Text, nullable=True, comment="技术要求")
    quality_requirements = Column(Text, nullable=True, comment="质量要求")
    remark = Column(Text, nullable=True,  # remark)
    created_by = Column(String(100), nullable=True,  # created_by)
    attachment_urls = Column(JSON, nullable=True,  # attachment_urls)
    org_id = Column(Integer, nullable=True,  # org_id)
    created_at = Column(DateTime, default=datetime.utcnow,  # created_at)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,  # updated_at)

    partner = relationship("OutsourcePartner", back_populates="orders")
    items = relationship("OutsourceOrderItem", back_populates="order",
                          cascade="all, delete-orphan", passive_deletes=True)
    quality_records = relationship("OutsourceQualityRecord", back_populates="order",
                                    cascade="all, delete-orphan", passive_deletes=True)


class OutsourceOrderItem(Base):
    """外协订单明细"""
    __tablename__ = "outsource_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    order_id = Column(Integer, ForeignKey("outsource_orders.id", ondelete="CASCADE"), nullable=False,  # order_id)
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格")
    quantity = Column(Float, default=1.0,  # quantity)
    unit = Column(String(20), default="个",  # unit)
    unit_price = Column(Float, default=0.0,  # unit_price)
    total_price = Column(Float, default=0.0,  # total_price)
    delivery_date = Column(Date, nullable=True,  # delivery_date)
    received_qty = Column(Float, default=0.0, comment="已收货数量")
    remark = Column(String(500), nullable=True,  # remark)
    sort_order = Column(Integer, default=0,  # sort_order)
    org_id = Column(Integer, nullable=True,  # org_id)
    created_at = Column(DateTime, default=datetime.utcnow,  # created_at)

    order = relationship("OutsourceOrder", back_populates="items")


# ── ③ 外协质检记录 ──

class OutsourceQualityRecord(Base):
    """外协质检记录"""
    __tablename__ = "outsource_quality_records"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    order_id = Column(Integer, ForeignKey("outsource_orders.id", ondelete="CASCADE"), nullable=False,  # order_id)
    inspect_type = Column(String(50), nullable=False, default="incoming", comment="质检类型: incoming/process/final")
    inspect_date = Column(Date, nullable=False, comment="检验日期")
    inspector = Column(String(100), nullable=True, comment="检验员")
    sample_qty = Column(Integer, default=0, comment="抽检数量")
    defect_qty = Column(Integer, default=0, comment="不合格数量")
    result = Column(String(20), nullable=False, default="pass", comment="结果: pass/fail/conditional")
    defect_description = Column(Text, nullable=True, comment="缺陷描述")
    conclusion = Column(Text, nullable=True, comment="检验结论")
    attachments = Column(JSON, nullable=True,  # attachments)
    org_id = Column(Integer, nullable=True,  # org_id)
    created_at = Column(DateTime, default=datetime.utcnow,  # created_at)

    order = relationship("OutsourceOrder", back_populates="quality_records")
    files = relationship("OutsourceQualityFile", back_populates="record",
                          cascade="all, delete-orphan", passive_deletes=True)


class OutsourceQualityFile(Base):
    """质检附件"""
    __tablename__ = "outsource_quality_files"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    record_id = Column(Integer, ForeignKey("outsource_quality_records.id", ondelete="CASCADE"), nullable=False,  # record_id)
    file_name = Column(String(200), nullable=False,  # file_name)
    file_url = Column(String(500), nullable=False,  # file_url)
    file_type = Column(String(50), nullable=True,  # file_type)
    file_size = Column(Integer, nullable=True,  # file_size)
    org_id = Column(Integer, nullable=True,  # org_id)
    created_at = Column(DateTime, default=datetime.utcnow,  # created_at)

    record = relationship("OutsourceQualityRecord", back_populates="files")
