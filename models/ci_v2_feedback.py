"""M4 Feedback Loop — 预测结果反馈与模型权重管理模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Numeric, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PredictionOutcome(Base):
    """预测结果反馈记录 — 收集实际执行结果 vs 预测对比"""
    __tablename__ = "ci_prediction_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    ecr_id = Column(Integer, ForeignKey("ecr_requests.id"), nullable=False, index=True, comment="关联ECR")
    risk_score = Column(Numeric(5, 2), nullable=False, comment="当时的风险分数")
    risk_level = Column(String(20), nullable=False, comment="当时的风险等级")
    predicted_action = Column(String(30), nullable=True, comment="预测的推荐动作 (AUTO_APPROVE/FAST_TRACK/FULL_APPROVAL/REJECT_REDESIGN)")
    actual_outcome = Column(String(30), nullable=False, comment="实际结果: approved/rejected/bom_success/bom_failure/cancelled")
    outcome_detail = Column(JSON, nullable=True, comment="结果详情JSON (如驳回原因、偏差金额等)")
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="记录时间")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    ecr = relationship("ECRRequest", foreign_keys=[ecr_id])


class ModelWeightSnapshot(Base):
    """模型权重版本快照 — 支持回滚"""
    __tablename__ = "ci_model_weight_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    version_id = Column(String(36), unique=True, nullable=False, index=True, comment="UUID版本标识")
    weights = Column(JSON, nullable=False, comment="权重配置: {bom_impact:0.3, cert_impact:0.2, ...}")
    sample_count = Column(Integer, default=0, comment="训练样本数")
    source_outcomes = Column(JSON, nullable=True, comment="样本来源概述")
    is_active = Column(Integer, default=0, comment="是否当前活跃版本: 0=否, 1=是")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
