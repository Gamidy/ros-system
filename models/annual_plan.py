"""年度规划数据模型

AnnualPlan 代表产品经理创建的年度规划条目。
项目通过 annual_planning_ref 字段关联到年度规划。
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, UniqueConstraint
from app.core.database import Base


class AnnualPlan(Base):
    """年度规划"""
    __tablename__ = "annual_plans"
    __table_args__ = (
        UniqueConstraint('name', 'year', name='uq_annual_plan_name_year'),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    name = Column(String(200), nullable=False, comment="年度规划名称")
    year = Column(Integer, nullable=False, index=True, comment="规划年度，如2027")
    description = Column(Text, nullable=True, comment="规划描述")
    doc_ref = Column(String(500), nullable=True, comment="文档引用/链接")
    owner = Column(String(50), nullable=False, index=True, comment="创建者用户名")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)
