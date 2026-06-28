"""8D报告模型 — 质量工程师P0"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, func
from app.core.database import Base


class EightDReport(Base):
    """8D报告 — 问题解决标准化流程"""
    __tablename__ = "eight_d_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_no = Column(String(50), unique=True, index=True, nullable=False, comment="报告编号（8D-YYYYMMDD-XXXX）")
    issue_title = Column(String(300), nullable=False, comment="问题标题")
    issue_desc = Column(Text, nullable=True, comment="问题描述")
    severity = Column(String(20), default="C", comment="严重程度(A-致命/B-严重/C-轻微)")
    product_info = Column(String(300), nullable=True, comment="关联产品/物料信息")

    # 8D流程各步骤内容
    d1_team = Column(Text, nullable=True, comment="D1-组建团队")
    d2_problem_desc = Column(Text, nullable=True, comment="D2-问题描述")
    d3_containment = Column(Text, nullable=True, comment="D3-遏制措施")
    d4_root_cause = Column(Text, nullable=True, comment="D4-根因分析")
    d5_corrective_action = Column(Text, nullable=True, comment="D5-纠正措施")
    d6_implement = Column(Text, nullable=True, comment="D6-措施实施")
    d7_prevention = Column(Text, nullable=True, comment="D7-预防措施")
    d8_closure = Column(Text, nullable=True, comment="D8-总结关闭")

    # 状态流转: open → analysis → containment → corrective → verify → closed
    status = Column(String(30), default="open", comment="状态")
    responsible_person = Column(String(100), nullable=True, comment="负责人")
    target_date = Column(Date, nullable=True, comment="目标关闭日期")
    closed_date = Column(DateTime, nullable=True, comment="实际关闭时间")
    remark = Column(Text, nullable=True, comment="备注")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
