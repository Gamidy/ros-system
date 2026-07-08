"""M1 Risk Engine — 风险评估记录模型

RiskAssessment: 5信号维度风险评分的持久化记录
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, JSON, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RiskAssessment(Base):
    """风险评估记录 — 每次风险引擎计算结果的持久化快照"""
    __tablename__ = "ci_risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    ecr_id = Column(Integer, ForeignKey("ecr_requests.id"), nullable=False, index=True,  # ecr_id)
    risk_score = Column(Numeric(5, 2), nullable=False, comment="总分0-100")
    risk_level = Column(String(20), nullable=False, comment="LOW/MEDIUM/HIGH/CRITICAL")

    # 5个信号维度分
    bom_impact = Column(Numeric(5, 2), default=0,  # bom_impact)
    cert_impact = Column(Numeric(5, 2), default=0,  # cert_impact)
    proto_instability = Column(Numeric(5, 2), default=0,  # proto_instability)
    cost_overrun = Column(Numeric(5, 2), default=0,  # cost_overrun)
    hist_failure_rate = Column(Numeric(5, 2), default=0,  # hist_failure_rate)

    signal_details = Column(JSON, nullable=True, comment="信号详情JSON")
    mitigation_suggestions = Column(JSON, nullable=True, comment="缓解建议列表")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    # 关系
    ecr = relationship("ECRRequest")
