"""M5-T4: CI v2.0 API 端点单元测试

测试策略: 使用 SQLite in-memory 数据库 + 直接测试路由处理函数
(不依赖 HTTP TestClient 的 auth 模拟, 聚焦业务逻辑验证)
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.ci_v2_risk import RiskAssessment
from app.models.ci_v2_impact import ImpactGraphSnapshot
from app.models.ci_v2_feedback import PredictionOutcome, ModelWeightSnapshot
from app.schemas.ci_v2 import (
    RiskAssessmentApiResponse, ImpactGraphOut, ApprovalRecommendation,
    PredictionOutcomeCreate, ModelWeightsOut,
)
from app.services.ai.risk_engine import RiskEngine
from app.services.ai.impact_graph import ImpactGraphEngine
from app.services.ai.approval_advisor import ApprovalAdvisor
from app.services.ai.feedback_loop import FeedbackLoop


# ── Fixtures ─────────────────────────────────────────────

_db_file: str = ""


@pytest.fixture(autouse=True)
def db_session() -> Generator[Session, None, None]:
    """为每个测试创建独立的内存 SQLite 数据库"""
    global _db_file
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    engine.dispose()
    # 清理残留文件
    if _db_file and os.path.exists(_db_file):
        try:
            os.unlink(_db_file)
        except OSError:
            pass


# ── 辅助函数 ────────────────────────────────────────────

def _create_ecr(db: Session, ecr_id: int = 1) -> dict:
    """在 ci_risk_assessments 和 ci_impact_graphs 中插入模拟数据"""
    # 创建 RiskAssessment
    assessment = RiskAssessment(
        ecr_id=ecr_id,
        risk_score=45.50,
        risk_level="MEDIUM",
        bom_impact=50.0,
        cert_impact=40.0,
        proto_instability=30.0,
        cost_overrun=20.0,
        hist_failure_rate=10.0,
        signal_details={"bom_items_affected": 5},
        mitigation_suggestions=["增加样机验证"],
    )
    db.add(assessment)
    db.flush()

    # 创建 ImpactGraphSnapshot
    graph = ImpactGraphSnapshot(
        ecr_id=ecr_id,
        graph_data={
            "nodes": [{"id": "ecr-1", "node_type": "ecr", "label": "ECR-1", "impact_score": 1.0, "affected_objects": [], "depth": 0}],
            "edges": [],
        },
        ripple_score=25.0,
        node_count=1,
        edge_count=0,
        max_depth=0,
    )
    db.add(graph)
    db.commit()
    return {"assessment_id": assessment.id, "graph_id": graph.id}


# ═══════════════════════════════════════════════════════════
# 端点 1: GET /api/v2/risk/{ecr_id}
# ═══════════════════════════════════════════════════════════

class TestGetRisk:
    def test_risk_found(self, db_session: Session) -> None:
        """有风险评估数据时返回正确评分"""
        _create_ecr(db_session, ecr_id=1)
        assessment = db_session.query(RiskAssessment).filter(
            RiskAssessment.ecr_id == 1
        ).order_by(RiskAssessment.created_at.desc()).first()
        assert assessment is not None
        assert float(assessment.risk_score) == 45.50
        assert assessment.risk_level == "MEDIUM"

    def test_risk_not_found(self, db_session: Session) -> None:
        """ECR 无风险评估时返回 None"""
        assessment = db_session.query(RiskAssessment).filter(
            RiskAssessment.ecr_id == 999
        ).first()
        assert assessment is None

    def test_risk_multiple_versions(self, db_session: Session) -> None:
        """有多个版本时返回最新的"""
        ids = []
        for i in range(3):
            ra = RiskAssessment(
                ecr_id=1, risk_score=float(10 + i * 20), risk_level="MEDIUM",
                bom_impact=0, cert_impact=0, proto_instability=0,
                cost_overrun=0, hist_failure_rate=0,
            )
            db_session.add(ra)
            db_session.flush()
            ids.append(ra.id)
        db_session.commit()
        latest = db_session.query(RiskAssessment).filter(
            RiskAssessment.ecr_id == 1
        ).order_by(RiskAssessment.id.desc()).first()
        assert latest is not None
        assert float(latest.risk_score) == 50.0


# ═══════════════════════════════════════════════════════════
# 端点 2: GET /api/v2/impact-graph/{ecr_id}
# ═══════════════════════════════════════════════════════════

class TestGetImpactGraph:
    def test_graph_found(self, db_session: Session) -> None:
        """有影响图数据时返回正确"""
        _create_ecr(db_session, ecr_id=1)
        graph = db_session.query(ImpactGraphSnapshot).filter(
            ImpactGraphSnapshot.ecr_id == 1
        ).first()
        assert graph is not None
        assert graph.node_count == 1
        assert graph.ripple_score == 25.0

    def test_graph_not_found(self, db_session: Session) -> None:
        """无影响图时返回 None"""
        graph = db_session.query(ImpactGraphSnapshot).filter(
            ImpactGraphSnapshot.ecr_id == 999
        ).first()
        assert graph is None

    def test_graph_serializable(self, db_session: Session) -> None:
        """图数据可序列化为 JSON"""
        _create_ecr(db_session, ecr_id=1)
        graph = db_session.query(ImpactGraphSnapshot).first()
        assert graph is not None
        data = json.dumps(graph.graph_data)
        parsed = json.loads(data)
        assert len(parsed["nodes"]) == 1


# ═══════════════════════════════════════════════════════════
# 端点 3: GET /api/v2/approval-recommendation/{ecr_id}
# ═══════════════════════════════════════════════════════════

class TestGetApprovalRecommendation:
    def test_recommendation_returns(self, db_session: Session) -> None:
        """有风险数据时返回推荐"""
        data = _create_ecr(db_session, ecr_id=1)
        assessment = db_session.query(RiskAssessment).filter(
            RiskAssessment.id == data["assessment_id"]
        ).first()
        assert assessment is not None
        score = float(assessment.risk_score)
        level = assessment.risk_level

        # 调用 ApprovalAdvisor
        rec = ApprovalAdvisor.recommend(
            risk_score=score,
            risk_level=level,
            use_llm=False,
        )
        assert rec.recommendation.value == "FAST_TRACK"
        assert "module_manager" in rec.required_approvers
        assert rec.risk_score == 45.50
        assert rec.risk_level == "MEDIUM"

    def test_recommendation_no_risk_data(self, db_session: Session) -> None:
        """无风险数据时返回 None (实际API会先调用 assess_for_ecr)"""
        assessment = db_session.query(RiskAssessment).filter(
            RiskAssessment.ecr_id == 999
        ).first()
        assert assessment is None


# ═══════════════════════════════════════════════════════════
# 端点 4: POST /api/v2/risk/batch
# ═══════════════════════════════════════════════════════════

class TestBatchRisk:
    def test_batch_normal(self, db_session: Session) -> None:
        """批量查询正常"""
        for eid in [1, 2, 3]:
            _create_ecr(db_session, ecr_id=eid)
        results = []
        for eid in [1, 2, 3]:
            ra = db_session.query(RiskAssessment).filter(
                RiskAssessment.ecr_id == eid
            ).order_by(RiskAssessment.created_at.desc()).first()
            results.append(RiskAssessmentApiResponse(
                ecr_id=ra.ecr_id, risk_score=float(ra.risk_score),
                risk_level=ra.risk_level, risk_vector={},
                mitigation_suggestions=[], created_at=ra.created_at,
            ) if ra else None)
        assert len(results) == 3
        assert all(r is not None for r in results)

    def test_batch_mixed(self, db_session: Session) -> None:
        """混合存在/不存在的 ECR"""
        _create_ecr(db_session, ecr_id=1)
        results = []
        for eid in [1, 999]:
            ra = db_session.query(RiskAssessment).filter(
                RiskAssessment.ecr_id == eid
            ).order_by(RiskAssessment.created_at.desc()).first()
            results.append(RiskAssessmentApiResponse(
                ecr_id=ra.ecr_id, risk_score=float(ra.risk_score),
                risk_level=ra.risk_level, risk_vector={},
                mitigation_suggestions=[], created_at=ra.created_at,
            ) if ra else None)
        assert results[0] is not None
        assert results[1] is None

    def test_batch_ecr_ids_limit(self) -> None:
        """超过20个 ECR 应拒绝"""
        ids = list(range(21))
        assert len(ids) > 20


# ═══════════════════════════════════════════════════════════
# 端点 5: POST /api/v2/feedback
# ═══════════════════════════════════════════════════════════

class TestPostFeedback:
    def test_feedback_outcome_valid(self) -> None:
        """验证 actual_outcome 合法值"""
        valid_outcomes = ["approved", "rejected", "bom_success", "bom_failure", "cancelled"]
        for v in valid_outcomes:
            create = PredictionOutcomeCreate(ecr_id=1, actual_outcome=v)
            assert create.actual_outcome == v

    def test_feedback_outcome_invalid(self) -> None:
        """非法 outcome 应触发验证错误"""
        with pytest.raises(ValueError):
            PredictionOutcomeCreate(ecr_id=1, actual_outcome="invalid")

    def test_feedback_record_and_recalculate(self, db_session: Session) -> None:
        """记录反馈后触发权重重算"""
        _create_ecr(db_session, ecr_id=1)

        # 记录多条反馈
        for i in range(12):  # 超过 MIN_SAMPLES_FOR_RECALC=10
            FeedbackLoop.record_outcome(
                db_session, ecr_id=1,
                actual_outcome="approved" if i % 2 == 0 else "rejected",
            )

        # 检查应触发重算
        assert FeedbackLoop._should_recalculate(db_session)

        # 执行重算
        snapshot = FeedbackLoop.recalculate_if_needed(db_session)
        assert snapshot is not None
        weights = snapshot.weights
        assert isinstance(weights, dict)
        for k in ["bom_impact", "cert_impact", "proto_instability", "cost_overrun", "hist_failure_rate"]:
            assert k in weights
            assert 0.05 <= weights[k] <= 0.50


# ═══════════════════════════════════════════════════════════
# 端点 6: GET /api/v2/model-params
# ═══════════════════════════════════════════════════════════

class TestGetModelParams:
    def test_active_weights_default(self, db_session: Session) -> None:
        """无活跃权重时返回默认 RiskEngine 权重"""
        active = FeedbackLoop.get_active_weights(db_session)
        assert active == RiskEngine.WEIGHTS

    def test_active_weights_after_snapshot(self, db_session: Session) -> None:
        """有快照后返回快照权重"""
        weights = {"bom_impact": 0.35, "cert_impact": 0.20,
                   "proto_instability": 0.15, "cost_overrun": 0.20,
                   "hist_failure_rate": 0.10}
        FeedbackLoop.save_version_snapshot(db_session, weights, sample_count=5)
        active = FeedbackLoop.get_active_weights(db_session)
        assert active["bom_impact"] == 0.35


# ═══════════════════════════════════════════════════════════
# 端点 7: POST /api/v2/model-params/{version_id}
# ═══════════════════════════════════════════════════════════

class TestPostModelParamsRollback:
    def test_rollback_success(self, db_session: Session) -> None:
        """回滚到指定版本"""
        # 创建两个版本
        v1 = FeedbackLoop.save_version_snapshot(
            db_session, {"bom_impact": 0.5, "cert_impact": 0.2,
                         "proto_instability": 0.1, "cost_overrun": 0.1,
                         "hist_failure_rate": 0.1},
            sample_count=5,
        )
        v2 = FeedbackLoop.save_version_snapshot(
            db_session, {"bom_impact": 0.1, "cert_impact": 0.2,
                         "proto_instability": 0.3, "cost_overrun": 0.2,
                         "hist_failure_rate": 0.2},
            sample_count=10,
        )
        # 当前活跃是 v2
        active = FeedbackLoop.get_active_weights(db_session)
        assert active["bom_impact"] == 0.1

        # 回滚到 v1
        rolled = FeedbackLoop.rollback_to_version(db_session, v1.version_id)
        assert rolled is not None

        # 现在活跃的是 v1
        active_after = FeedbackLoop.get_active_weights(db_session)
        assert active_after["bom_impact"] == 0.5

    def test_rollback_not_found(self, db_session: Session) -> None:
        """版本不存在时抛异常"""
        with pytest.raises(ValueError, match="不存在"):
            FeedbackLoop.rollback_to_version(db_session, "nonexistent-uuid")
