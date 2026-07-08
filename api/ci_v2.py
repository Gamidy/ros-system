"""M5-T1: CI v2.0 API — 变更智能评估系统 v2.0 端点

包含 7 个端点:
  1. GET  /api/v2/risk/{ecr_id}                — 风险评分
  2. GET  /api/v2/impact-graph/{ecr_id}         — 变更影响图
  3. GET  /api/v2/approval-recommendation/{ecr_id} — 审批推荐
  4. POST /api/v2/risk/batch                    — 批量风险评分
  5. POST /api/v2/feedback                      — 提交预测反馈
  6. GET  /api/v2/model-params                  — 查询模型参数
  7. POST /api/v2/model-params/{version_id}     — 回滚模型参数

全类型注解，无 Any，无裸 except。
所有端点 tags=["CI v2.0"]。
M4-T3 (FeedbackLoop) 使用惰性导入，即使未完成也不崩溃。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_menu
from app.models.ci_v2_feedback import ModelWeightSnapshot
from app.models.ci_v2_impact import ImpactGraphSnapshot
from app.models.ci_v2_risk import RiskAssessment
from app.schemas.ci_v2 import (
    ApprovalRecommendation,
    ImpactGraphOut,
    ModelWeightsOut,
    PredictionOutcomeCreate,
    PredictionOutcomeOut,
    RiskAssessmentApiResponse,
)
from app.services.ai.approval_advisor import ApprovalAdvisor
from app.services.ai.risk_engine import RiskEngine

# ── 惰性导入 (M4-T3 FeedbackLoop 可能未完成) ──────────────────────
try:
    from app.services.ai.feedback_loop import FeedbackLoop
except ImportError:
    FeedbackLoop = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["CI v2.0"])


# ── 请求体 / 响应体 Schemas ─────────────────────────────────────────

class RiskBatchInput(BaseModel):
    """批量风险评分请求体"""
    ecr_ids: list[int]


class ModelParamsResponse(BaseModel):
    """模型参数查询响应"""
    active: ModelWeightsOut
    history: list[ModelWeightsOut]


# ── 辅助函数 ────────────────────────────────────────────────────────

def _get_latest_risk_assessment(
    db: Session, ecr_id: int,
) -> Optional[RiskAssessment]:
    """查询 ECR 的最新 RiskAssessment 记录"""
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.ecr_id == ecr_id)
        .order_by(RiskAssessment.created_at.desc())
        .first()
    )


def _get_latest_impact_snapshot(
    db: Session, ecr_id: int,
) -> Optional[ImpactGraphSnapshot]:
    """查询 ECR 的最新 ImpactGraphSnapshot 记录"""
    return (
        db.query(ImpactGraphSnapshot)
        .filter(ImpactGraphSnapshot.ecr_id == ecr_id)
        .order_by(ImpactGraphSnapshot.created_at.desc())
        .first()
    )


def _deserialize_impact_graph(snapshot: ImpactGraphSnapshot) -> ImpactGraphOut:
    """将 ImpactGraphSnapshot.graph_data 反序列化为 ImpactGraphOut"""
    data = snapshot.graph_data
    if isinstance(data, dict):
        return ImpactGraphOut(**data)
    return data


def _risk_assessment_to_api_response(ra: RiskAssessment) -> RiskAssessmentApiResponse:
    """将 RiskAssessment ORM 对象转换为 API 响应"""
    return RiskAssessmentApiResponse(
        ecr_id=ra.ecr_id,
        risk_score=float(ra.risk_score),
        risk_level=ra.risk_level,
        risk_vector=ra.signal_details if ra.signal_details is not None else {},
        mitigation_suggestions=(
            ra.mitigation_suggestions if ra.mitigation_suggestions is not None else []
        ),
        created_at=ra.created_at,
    )


def _build_default_active_weights() -> ModelWeightsOut:
    """兜底：无活跃权重时返回 RiskEngine 默认权重"""
    return ModelWeightsOut(
        version_id="default",
        weights=RiskEngine.WEIGHTS.copy(),
        sample_count=0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def _model_weight_to_out(record: ModelWeightSnapshot) -> ModelWeightsOut:
    """将 ModelWeightSnapshot ORM 对象转换为 ModelWeightsOut"""
    return ModelWeightsOut(
        version_id=record.version_id,
        weights=record.weights,
        sample_count=record.sample_count,
        is_active=bool(record.is_active),
        created_at=record.created_at,
    )


# ═══════════════════════════════════════════════════════════════════
# 1. GET /api/v2/risk/{ecr_id}
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/risk/{ecr_id}",
    response_model=RiskAssessmentApiResponse,
    dependencies=[Depends(require_menu("changes"))],
)
def get_risk(
    ecr_id: int,
    db: Session = Depends(get_db),
) -> RiskAssessmentApiResponse:
    """查询最新风险评分

    ECR 不存在或无评分记录时返回 404。
    """
    ra = _get_latest_risk_assessment(db, ecr_id)
    if ra is None:
        raise HTTPException(status_code=404, detail="该 ECR 尚无风险评分")
    return _risk_assessment_to_api_response(ra)


# ═══════════════════════════════════════════════════════════════════
# 2. GET /api/v2/impact-graph/{ecr_id}
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/impact-graph/{ecr_id}",
    response_model=ImpactGraphOut,
    dependencies=[Depends(require_menu("changes"))],
)
def get_impact_graph(
    ecr_id: int,
    db: Session = Depends(get_db),
) -> ImpactGraphOut:
    """查询最新变更影响图

    无图数据时返回 404。
    """
    snapshot = _get_latest_impact_snapshot(db, ecr_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="该 ECR 尚无影响图数据")
    return _deserialize_impact_graph(snapshot)


# ═══════════════════════════════════════════════════════════════════
# 3. GET /api/v2/approval-recommendation/{ecr_id}
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/approval-recommendation/{ecr_id}",
    response_model=ApprovalRecommendation,
    dependencies=[Depends(require_menu("changes"))],
)
def get_approval_recommendation(
    ecr_id: int,
    db: Session = Depends(get_db),
) -> ApprovalRecommendation:
    """获取审批推荐

    流程:
      1. 查最新 RiskAssessment 获取 risk_score / risk_level
      2. 若无缓存评分 → 调用 RiskEngine.assess_for_ecr() 生成
      3. 查最新 ImpactGraphSnapshot（可选，用于丰富推荐理由）
      4. 调用 ApprovalAdvisor.recommend() 计算推荐
    """
    # 1. 获取风险数据
    ra = _get_latest_risk_assessment(db, ecr_id)

    if ra is None:
        # 无缓存评分 → 调用 RiskEngine 生成
        engine = RiskEngine()
        result = engine.assess_for_ecr(db, ecr_id)
        if result is None:
            raise HTTPException(status_code=404, detail="ECR 不存在，无法生成风险评分")
        risk_score = result.risk_score
        risk_level = result.risk_level.value
    else:
        risk_score = float(ra.risk_score)
        risk_level = ra.risk_level

    # 2. 获取影响图（可选）
    impact_graph: Optional[ImpactGraphOut] = None
    snapshot = _get_latest_impact_snapshot(db, ecr_id)
    if snapshot is not None:
        impact_graph = _deserialize_impact_graph(snapshot)

    # 3. 调用 ApprovalAdvisor 生成推荐
    return ApprovalAdvisor.recommend(
        risk_score=risk_score,
        risk_level=risk_level,
        impact_graph=impact_graph,
        use_llm=False,
    )


# ═══════════════════════════════════════════════════════════════════
# 4. POST /api/v2/risk/batch
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/risk/batch",
    response_model=list[Optional[RiskAssessmentApiResponse]],
    dependencies=[Depends(require_menu("changes"))],
)
def batch_risk(
    body: RiskBatchInput,
    db: Session = Depends(get_db),
) -> list[Optional[RiskAssessmentApiResponse]]:
    """批量查询风险评分（最多 20 个 ECR）

    不存在的 ECR 用 None 占位。
    超过 20 个返回 400。
    """
    if len(body.ecr_ids) > 20:
        raise HTTPException(
            status_code=400,
            detail="批量查询最多支持 20 个 ECR",
        )

    results: list[Optional[RiskAssessmentApiResponse]] = []
    for ecr_id in body.ecr_ids:
        ra = _get_latest_risk_assessment(db, ecr_id)
        if ra is None:
            results.append(None)
        else:
            results.append(_risk_assessment_to_api_response(ra))
    return results


# ═══════════════════════════════════════════════════════════════════
# 5. POST /api/v2/feedback
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/feedback",
    response_model=PredictionOutcomeOut,
    dependencies=[Depends(require_menu("changes"))],
)
def submit_feedback(
    body: PredictionOutcomeCreate,
    db: Session = Depends(get_db),
) -> PredictionOutcomeOut:
    """提交预测反馈

    记录实际结果并触发权重重算。
    依赖 FeedbackLoop（M4-T3），若未就绪则返回 503。
    """
    if FeedbackLoop is None:
        raise HTTPException(
            status_code=503,
            detail="FeedbackLoop 模块尚未就绪（M4-T3 未完成）",
        )

    loop = FeedbackLoop()
    outcome = loop.record_outcome(db, body)
    loop.recalculate_if_needed(db)
    return outcome


# ═══════════════════════════════════════════════════════════════════
# 6. GET /api/v2/model-params
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/model-params",
    response_model=ModelParamsResponse,
    dependencies=[Depends(require_menu("changes"))],
)
def get_model_params(
    db: Session = Depends(get_db),
) -> ModelParamsResponse:
    """查询模型参数（活跃权重 + 历史版本）

    无活跃权重时使用 RiskEngine.WEIGHTS 默认值。
    """
    # 查询活跃权重
    active_record = (
        db.query(ModelWeightSnapshot)
        .filter(ModelWeightSnapshot.is_active == 1)
        .order_by(ModelWeightSnapshot.created_at.desc())
        .first()
    )

    # 查询全部历史版本（按创建时间降序）
    history_records = (
        db.query(ModelWeightSnapshot)
        .order_by(ModelWeightSnapshot.created_at.desc())
        .all()
    )

    history: list[ModelWeightsOut] = [
        _model_weight_to_out(rec) for rec in history_records
    ]

    if active_record is not None:
        active = _model_weight_to_out(active_record)
        # 确保 active 的 is_active=True
        active.is_active = True
    else:
        active = _build_default_active_weights()

    return ModelParamsResponse(active=active, history=history)


# ═══════════════════════════════════════════════════════════════════
# 7. POST /api/v2/model-params/{version_id}
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/model-params/{version_id}",
    response_model=ModelWeightsOut,
    dependencies=[Depends(require_menu("changes"))],
)
def rollback_model_params(
    version_id: str,
    db: Session = Depends(get_db),
) -> ModelWeightsOut:
    """回滚模型参数到指定版本

    依赖 FeedbackLoop（M4-T3），若未就绪则返回 503。
    版本不存在时返回 404。
    """
    if FeedbackLoop is None:
        raise HTTPException(
            status_code=503,
            detail="FeedbackLoop 模块尚未就绪（M4-T3 未完成）",
        )

    loop = FeedbackLoop()
    result = loop.rollback_to_version(db, version_id)
    if result is None:
        raise HTTPException(status_code=404, detail="指定的版本不存在")
    return result
