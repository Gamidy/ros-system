"""来料检验(IQC)管理"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Float, Boolean
from app.core.database import Base


class IQCRecord(Base):
    """来料检验记录"""
    __tablename__ = "iqc_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    receipt_no = Column(String(50), nullable=True, comment="收货单号")
    supplier = Column(String(100), nullable=False, comment="供应商")
    part_code = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    batch_no = Column(String(50), nullable=True, comment="批次号")
    quantity = Column(Integer, default=0, comment="送检数量")
    sample_qty = Column(Integer, default=0, comment="抽样数量")
    accept_qty = Column(Integer, default=0, comment="合格数量")
    reject_qty = Column(Integer, default=0, comment="不合格数量")
    aql = Column(String(20), default="0.65", comment="AQL接受质量限")
    inspection_level = Column(String(20), default="II", comment="检验水平")
    verdict = Column(String(20), default="pending", comment="判定: pending/accept/reject/conditional")
    inspector = Column(String(50), nullable=True, comment="检验员")
    inspect_date = Column(Date, nullable=True, comment="检验日期")
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class IQCItem(Base):
    """IQC检验项明细"""
    __tablename__ = "iqc_items"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("iqc_records.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(100), nullable=False, comment="检验项名称")
    spec = Column(String(200), nullable=True, comment="规格要求")
    measured = Column(String(100), nullable=True, comment="实测值")
    result = Column(String(20), default="pass", comment="pass/fail/na")
    remark = Column(Text, nullable=True)
