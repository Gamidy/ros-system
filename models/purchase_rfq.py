"""询比价管理(RFQ)"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Float
from app.core.database import Base


class RFQ(Base):
    """询价单"""
    __tablename__ = "rfqs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    rfq_no = Column(String(50), unique=True, nullable=False, comment="询价单号")
    title = Column(String(200), nullable=False, comment="询价标题")
    # 物料清单 JSON: [{"part_code":"...","part_name":"...","qty":100,"spec":"..."}]
    items = Column(Text, nullable=True, comment="物料清单JSON")
    # 邀请供应商 JSON: [{"supplier_name":"...","contact":"...","email":"..."}]
    suppliers = Column(Text, nullable=True, comment="邀请供应商JSON")
    deadline = Column(Date, nullable=True, comment="报价截止日期")
    status = Column(String(20), default="draft", comment="draft/sent/quoting/closed/cancelled")
    created_by = Column(String(50), nullable=True,  # created_by)
    remark = Column(Text, nullable=True,  # remark)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)


class RFQQuotation(Base):
    """供应商报价"""
    __tablename__ = "rfq_quotations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    rfq_id = Column(Integer, ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False,  # rfq_id)
    supplier_name = Column(String(100), nullable=False, comment="供应商名称")
    # 报价明细 JSON: [{"part_code":"...","unit_price":12.5,"moq":100,"lead_time":"30天"}]
    items = Column(Text, nullable=True, comment="报价明细JSON")
    total_amount = Column(Float, default=0, comment="总价")
    delivery_days = Column(Integer, nullable=True, comment="交期(天)")
    payment_terms = Column(String(100), nullable=True, comment="付款条件")
    valid_until = Column(Date, nullable=True, comment="报价有效期")
    contact = Column(String(50), nullable=True,  # contact)
    remark = Column(Text, nullable=True,  # remark)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
