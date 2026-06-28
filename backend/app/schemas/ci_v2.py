"""CIE v2.0 — Pydantic Schema 定义

包含 M1 Risk Engine + M2 Impact Graph + M3 Approval Advisor 的全部 Schema。
全类型注解，无 Any。
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ════════════════════════════════════════════════════
# M1 — Risk Engine Schema
# ════════════════════════════════════════════════════

class RiskLevelEnum(str, Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationEnum(str, Enum):
    """推荐处理方式"""
    AUTO_APPROVE = "AUTO_APPROVE"
    FAST_TRACK = "FAST_TRACK"
    FULL_APPROVAL = "FULL_APPROVAL"
    REJECT_REDESIGN = "REJECT_REDESIGN"


class SignalInput(BaseModel):
    """风险信号输入 — 5个维度，范围0-100

    所有字段默认为0，支持输入缺失时的优雅降级。
    """
    bom_impact: float = Field(default=0, ge=0, le=100, description="BOM影响度")
    cert_impact: float = Field(default=0, ge=0, le=100, description="认证影响度")
    proto_instability: float = Field(default=0, ge=0, le=100, description="样机不稳定性")
    cost_overrun: float = Field(default=0, ge=0, le=100, description="成本超支风险")
    hist_failure_rate: float = Field(default=0, ge=0, le=100, description="历史故障率")

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentOut(BaseModel):
    """风险评估完整输出"""
    id: int
    ecr_id: int
    risk_score: float
    risk_level: RiskLevelEnum

    # 5个信号维度分
    bom_impact: float = 0
    cert_impact: float = 0
    proto_instability: float = 0
    cost_overrun: float = 0
    hist_failure_rate: float = 0

    signal_details: Optional[dict] = None
    mitigation_suggestions: Optional[list[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ════════════════════════════════════════════════════
# M2 — Impact Graph Schema
# ════════════════════════════════════════════════════

class ImpactNode(BaseModel):
    """DAG 节点 — 代表变更传播链上的一个环节"""
    id: str
    node_type: str
    label: str
    impact_score: float
    affected_objects: list[dict]
    depth: int
    model_config = ConfigDict(from_attributes=True)


class ImpactEdge(BaseModel):
    """DAG 边 — 代表变更传播关系"""
    source_id: str
    target_id: str
    weight: float
    label: str
    model_config = ConfigDict(from_attributes=True)


class ImpactGraphOut(BaseModel):
    """变更影响图完整输出"""
    nodes: list[ImpactNode]
    edges: list[ImpactEdge]
    ripple_score: float
    max_depth: int
    node_count: int
    edge_count: int
    model_config = ConfigDict(from_attributes=True)


class RipplePath(BaseModel):
    """从根节点到叶子节点的一条完整传播路径"""
    path: list[str]
    total_score: float
    node_count: int
    model_config = ConfigDict(from_attributes=True)


# ════════════════════════════════════════════════════
# M3 — Approval Advisor Schema（预留）
# ════════════════════════════════════════════════════

class ApprovalAdvisorAction(str, Enum):
    """审批推荐动作"""
    AUTO_APPROVE = "AUTO_APPROVE"
    FAST_TRACK = "FAST_TRACK"
    FULL_APPROVAL = "FULL_APPROVAL"
    REJECT_REDESIGN = "REJECT_REDESIGN"


class ApprovalRecommendation(BaseModel):
    """审批推荐输出"""
    recommendation: ApprovalAdvisorAction
    required_approvers: list[str]
    reason: str
    confidence: float
    risk_level: str
    risk_score: float
    model_config = ConfigDict(from_attributes=True)


# ════════════════════════════════════════════════════
# M5 — API Schema（预留）
# ════════════════════════════════════════════════════

class RiskAssessmentApiResponse(BaseModel):
    """风险评分 API 响应"""
    ecr_id: int
    risk_score: float
    risk_level: str
    risk_vector: dict
    mitigation_suggestions: list[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ════════════════════════════════════════════════════
# M4 — Feedback Loop Schema
# ════════════════════════════════════════════════════

ACTUAL_OUTCOME_CHOICES = ["approved", "rejected", "bom_success", "bom_failure", "cancelled"]


class PredictionOutcomeCreate(BaseModel):
    """反馈提交入参"""
    ecr_id: int
    actual_outcome: str  # 会在 validator 中检查
    outcome_detail: Optional[dict] = None

    @field_validator("actual_outcome")
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        if v not in ACTUAL_OUTCOME_CHOICES:
            raise ValueError(f"actual_outcome 必须是 {ACTUAL_OUTCOME_CHOICES} 之一, 收到: {v}")
        return v


class PredictionOutcomeOut(BaseModel):
    """反馈记录输出"""
    id: int
    ecr_id: int
    risk_score: float
    risk_level: str
    predicted_action: Optional[str] = None
    actual_outcome: str
    outcome_detail: Optional[dict] = None
    recorded_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ModelWeightsOut(BaseModel):
    """权重参数版本输出"""
    version_id: str
    weights: dict
    sample_count: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
