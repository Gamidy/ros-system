"""客户投诉管理"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from app.core.database import Base


class CustomerComplaint(Base):
    """客户投诉记录"""
    __tablename__ = "customer_complaints"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    complaint_no = Column(String(50), unique=True, nullable=False, comment="投诉编号")
    customer_name = Column(String(100), nullable=False, comment="客户名称")
    product_code = Column(String(50), nullable=True, comment="产品型号")
    batch_no = Column(String(50), nullable=True, comment="批次号")
    qty_involved = Column(Integer, default=0, comment="涉及数量")
    complaint_type = Column(String(30), default="quality", comment="类型: quality/delivery/service/other")
    severity = Column(String(20), default="medium", comment="严重程度: critical/high/medium/low")
    title = Column(String(200), nullable=False, comment="投诉标题")
    description = Column(Text, nullable=True, comment="投诉描述")
    root_cause = Column(Text, nullable=True, comment="根本原因")
    corrective_action = Column(Text, nullable=True, comment="纠正措施")
    preventive_action = Column(Text, nullable=True, comment="预防措施")
    status = Column(String(20), default="open", comment="open/investigation/action/verify/closed")
    handler = Column(String(50), nullable=True, comment="处理人")
    complain_date = Column(Date, nullable=True, comment="投诉日期")
    closed_date = Column(Date, nullable=True, comment="关闭日期")
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
