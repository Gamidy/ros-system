"""财务快照模型"""
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func


class FinancialSnapshot(Base):
    """财务快照"""
    __tablename__ = "financial_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), comment="期间 YYYY-MM")
    revenue = Column(Float, comment="销售收入(万元)")
    cost_of_sales = Column(Float, comment="销售成本(万元)")
    gross_profit_rate = Column(Float, nullable=True, comment="毛利率%")
    net_profit_rate = Column(Float, nullable=True, comment="净利润率%")
    r_and_d_budget = Column(Float, nullable=True, comment="研发预算(万元)")
    r_and_d_spent = Column(Float, nullable=True, comment="研发支出(万元)")
    data_source = Column(String(50), default="manual", comment="数据来源: erp/manual")
    created_at = Column(DateTime, server_default=func.now())
