"""M4-T5 FeedbackLoop 单元测试

测试 FeedbackLoop 类的全部 9 个方法：
  - record_outcome / get_outcomes
  - _should_recalculate
  - _collect_training_samples
  - _optimize_weights
  - save_version_snapshot / _cleanup_old_versions
  - get_active_weights
  - rollback_to_version
  - recalculate_if_needed

验收标准：
  1. ≥14 个测试全部通过
  2. 测试使用独立内存数据库 (不影响生产数据)
  3. 全类型注解
  4. 无裸 except
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.ci_v2_feedback import PredictionOutcome, ModelWeightSnapshot
from app.models.ci_v2_risk import RiskAssessment
from app.services.ai.feedback_loop import FeedbackLoop
from app.services.ai.risk_engine import RiskEngine

# 测试期间禁用日志输出
logging.disable(logging.CRITICAL)


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """创建独立的 SQLite in-memory 数据库 (不影响生产数据)"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ─── 辅助函数 ──────────────────────────────────────────────────────────


def _create_risk_assessment(
    db: Session,
    ecr_id: int = 1,
    risk_score: float = 45.0,
    risk_level: str = "MEDIUM",
    bom_impact: float = 30.0,
    cert_impact: float = 20.0,
    proto_instability: float = 10.0,
    cost_overrun: float = 15.0,
    hist_failure_rate: float = 5.0,
) -> RiskAssessment:
    """辅助创建 RiskAssessment 记录"""
    assessment = RiskAssessment(
        ecr_id=ecr_id,
        risk_score=Decimal(str(risk_score)),
        risk_level=risk_level,
        bom_impact=Decimal(str(bom_impact)),
        cert_impact=Decimal(str(cert_impact)),
        proto_instability=Decimal(str(proto_instability)),
        cost_overrun=Decimal(str(cost_overrun)),
        hist_failure_rate=Decimal(str(hist_failure_rate)),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def _create_outcome(
    db: Session,
    ecr_id: int = 1,
    risk_score: float = 45.0,
    risk_level: str = "MEDIUM",
    predicted_action: str = "FAST_TRACK",
    actual_outcome: str = "approved",
    outcome_detail: dict | None = None,
    recorded_at: datetime | None = None,
) -> PredictionOutcome:
    """辅助创建 PredictionOutcome 记录"""
    outcome = PredictionOutcome(
        ecr_id=ecr_id,
        risk_score=Decimal(str(risk_score)),
        risk_level=risk_level,
        predicted_action=predicted_action,
        actual_outcome=actual_outcome,
        outcome_detail=outcome_detail or {},
        recorded_at=recorded_at or datetime.now(timezone.utc),
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


# ─── Tests: record_outcome ─────────────────────────────────────────────


class TestRecordOutcome:
    """record_outcome 方法测试"""

    def test_record_outcome(self, db_session: Session) -> None:
        """record_outcome 成功创建 PredictionOutcome 记录"""
        assessment = _create_risk_assessment(db_session, ecr_id=10)

        outcome = FeedbackLoop.record_outcome(
            db=db_session,
            ecr_id=10,
            actual_outcome="approved",
            outcome_detail={"reason": "测试通过"},
        )

        assert outcome is not None
        assert outcome.id is not None
        assert outcome.ecr_id == 10
        assert outcome.actual_outcome == "approved"
        assert outcome.risk_score == assessment.risk_score
        assert outcome.risk_level == assessment.risk_level
        assert outcome.predicted_action == "FAST_TRACK"

        # 验证已持久化到数据库
        saved: PredictionOutcome | None = (
            db_session.query(PredictionOutcome)
            .filter(PredictionOutcome.ecr_id == 10)
            .first()
        )
        assert saved is not None
        assert saved.id == outcome.id

    def test_record_outcome_no_assessment(self, db_session: Session) -> None:
        """ecr 无 RiskAssessment 时抛 ValueError"""
        with pytest.raises(ValueError, match="没有关联的 RiskAssessment"):
            FeedbackLoop.record_outcome(
                db=db_session,
                ecr_id=999,
                actual_outcome="rejected",
            )


# ─── Tests: get_outcomes ───────────────────────────────────────────────


class TestGetOutcomes:
    """get_outcomes 方法测试"""

    def test_get_outcomes(self, db_session: Session) -> None:
        """查询反馈历史, 按时间倒序"""
        # 准备测试数据: 三条不同时间的记录
        now = datetime.now(timezone.utc)
        o1 = _create_outcome(
            db_session, ecr_id=20, actual_outcome="approved",
            recorded_at=now - timedelta(hours=3),
        )
        o2 = _create_outcome(
            db_session, ecr_id=20, actual_outcome="rejected",
            recorded_at=now - timedelta(hours=2),
        )
        o3 = _create_outcome(
            db_session, ecr_id=20, actual_outcome="approved",
            recorded_at=now - timedelta(hours=1),
        )

        outcomes = FeedbackLoop.get_outcomes(db_session, ecr_id=20)

        assert len(outcomes) == 3
        # 验证时间倒序: 最新的在前
        assert outcomes[0].id == o3.id
        assert outcomes[1].id == o2.id
        assert outcomes[2].id == o1.id

        # 验证 recorded_at 降序
        for i in range(len(outcomes) - 1):
            assert outcomes[i].recorded_at >= outcomes[i + 1].recorded_at


# ─── Tests: _should_recalculate ────────────────────────────────────────


class TestShouldRecalculate:
    """_should_recalculate 方法测试"""

    def test_should_recalculate_below_threshold(self, db_session: Session) -> None:
        """样本 < MIN_SAMPLES_FOR_RECALC (10) 时返回 False"""
        # 只有 5 条样本 < 10
        for i in range(5):
            _create_outcome(db_session, ecr_id=30 + i, actual_outcome="approved")

        assert FeedbackLoop._should_recalculate(db_session) is False

    def test_should_recalculate_above_threshold(self, db_session: Session) -> None:
        """样本 >= MIN_SAMPLES_FOR_RECALC 时返回 True"""
        for i in range(FeedbackLoop.MIN_SAMPLES_FOR_RECALC):
            _create_outcome(db_session, ecr_id=40 + i, actual_outcome="approved")

        assert FeedbackLoop._should_recalculate(db_session) is True

    def test_should_recalculate_after_snapshot(self, db_session: Session) -> None:
        """保存快照后, 应从新计数"""
        # 先创建 15 条样本
        for i in range(15):
            _create_outcome(db_session, ecr_id=50 + i, actual_outcome="approved")

        # 保存快照, 标记已训练 15 条
        FeedbackLoop.save_version_snapshot(
            db_session,
            weights=dict(RiskEngine.WEIGHTS),
            sample_count=15,
        )

        # 此时新样本 = 15 - 15 = 0, 不应触发重算
        assert FeedbackLoop._should_recalculate(db_session) is False

        # 再新增 10 条, 新样本 = 10, 触发重算
        for i in range(FeedbackLoop.MIN_SAMPLES_FOR_RECALC):
            _create_outcome(db_session, ecr_id=60 + i, actual_outcome="approved")

        assert FeedbackLoop._should_recalculate(db_session) is True


# ─── Tests: _collect_training_samples ──────────────────────────────────


class TestCollectTrainingSamples:
    """_collect_training_samples 方法测试"""

    def test_collect_training_samples(self, db_session: Session) -> None:
        """样本收集含 5 维度分数 + outcome"""
        assessment = _create_risk_assessment(
            db_session,
            ecr_id=70,
            bom_impact=40.0,
            cert_impact=30.0,
            proto_instability=20.0,
            cost_overrun=15.0,
            hist_failure_rate=10.0,
        )
        _create_outcome(
            db_session,
            ecr_id=70,
            risk_score=float(assessment.risk_score),
            risk_level=str(assessment.risk_level),
            actual_outcome="rejected",
        )

        samples: list[dict] = FeedbackLoop._collect_training_samples(db_session)

        assert len(samples) == 1
        sample = samples[0]
        assert sample["ecr_id"] == 70
        assert sample["actual_outcome"] == "rejected"
        assert sample["bom_impact"] == 40.0
        assert sample["cert_impact"] == 30.0
        assert sample["proto_instability"] == 20.0
        assert sample["cost_overrun"] == 15.0
        assert sample["hist_failure_rate"] == 10.0
        assert sample["risk_score"] == float(assessment.risk_score)


# ─── Tests: _optimize_weights ──────────────────────────────────────────


class TestOptimizeWeights:
    """_optimize_weights 方法测试"""

    def test_optimize_weights_bounds(self, db_session: Session) -> None:
        """所有权重 ∈ [0.05, 0.50]"""
        # 极端样本: bom_impact 高度突出 + 连续 rejected
        samples: list[dict] = [
            {
                "ecr_id": 80,
                "risk_score": 50.0,
                "risk_level": "MEDIUM",
                "bom_impact": 90.0,
                "cert_impact": 5.0,
                "proto_instability": 5.0,
                "cost_overrun": 5.0,
                "hist_failure_rate": 5.0,
                "actual_outcome": "rejected",
            }
        ] * 100

        current_weights: dict[str, float] = dict(RiskEngine.WEIGHTS)
        optimized: dict[str, float] = FeedbackLoop._optimize_weights(
            samples, current_weights,
        )

        for dim, w in optimized.items():
            assert 0.05 <= w <= 0.50, (
                f"权重 {dim}={w} 超出 [0.05, 0.50] 范围"
            )

    def test_optimize_weights_sum(self, db_session: Session) -> None:
        """权重之和 ≈ 1.0"""
        samples: list[dict] = [
            {
                "ecr_id": 81,
                "risk_score": 50.0,
                "risk_level": "MEDIUM",
                "bom_impact": 80.0,
                "cert_impact": 10.0,
                "proto_instability": 10.0,
                "cost_overrun": 10.0,
                "hist_failure_rate": 10.0,
                "actual_outcome": "approved",
            },
            {
                "ecr_id": 82,
                "risk_score": 60.0,
                "risk_level": "HIGH",
                "bom_impact": 30.0,
                "cert_impact": 60.0,
                "proto_instability": 40.0,
                "cost_overrun": 50.0,
                "hist_failure_rate": 20.0,
                "actual_outcome": "rejected",
            },
        ]

        current_weights: dict[str, float] = dict(RiskEngine.WEIGHTS)
        optimized: dict[str, float] = FeedbackLoop._optimize_weights(
            samples, current_weights,
        )

        total: float = sum(optimized.values())
        assert abs(total - 1.0) < 0.01, (
            f"权重之和 {total} 不等于 1.0 (差值 {abs(total - 1.0)})"
        )


# ─── Tests: save_version_snapshot ──────────────────────────────────────


class TestSaveVersionSnapshot:
    """save_version_snapshot 方法测试"""

    def test_save_version_snapshot(self, db_session: Session) -> None:
        """保存快照, 生成 UUID, 标记活跃"""
        weights: dict[str, float] = dict(RiskEngine.WEIGHTS)
        snapshot = FeedbackLoop.save_version_snapshot(
            db_session,
            weights=weights,
            sample_count=10,
        )

        assert snapshot is not None
        assert snapshot.id is not None
        # 验证 UUID 格式
        parsed_uuid = uuid.UUID(snapshot.version_id)
        assert str(parsed_uuid) == snapshot.version_id
        assert snapshot.weights == weights
        assert snapshot.sample_count == 10
        assert snapshot.is_active == 1

        # 保存第二个快照 → 第一个应不再活跃
        weights_v2: dict[str, float] = {
            "bom_impact": 0.25,
            "cert_impact": 0.20,
            "proto_instability": 0.20,
            "cost_overrun": 0.20,
            "hist_failure_rate": 0.15,
        }
        snapshot_v2 = FeedbackLoop.save_version_snapshot(
            db_session,
            weights=weights_v2,
            sample_count=20,
        )

        assert snapshot_v2.is_active == 1
        # 重新查询第一个快照, 确认已取消活跃
        db_session.expire_all()
        v1_fresh: ModelWeightSnapshot | None = (
            db_session.query(ModelWeightSnapshot)
            .filter(ModelWeightSnapshot.id == snapshot.id)
            .first()
        )
        assert v1_fresh is not None
        assert v1_fresh.is_active == 0


# ─── Tests: version_history_cleanup ────────────────────────────────────


class TestVersionHistoryCleanup:
    """_cleanup_old_versions / save_version_snapshot 自动清理测试"""

    def test_version_history_cleanup(self, db_session: Session) -> None:
        """超 MAX_VERSION_HISTORY 个版本时自动清理旧版"""
        base_weights: dict[str, float] = dict(RiskEngine.WEIGHTS)

        # 创建 MAX_VERSION_HISTORY + 5 个快照版本
        total_versions: int = FeedbackLoop.MAX_VERSION_HISTORY + 5
        for i in range(total_versions):
            FeedbackLoop.save_version_snapshot(
                db_session,
                weights=dict(base_weights),
                sample_count=i + 1,
            )

        # 验证总数不超过 MAX_VERSION_HISTORY
        remaining: int = db_session.query(ModelWeightSnapshot).count()
        assert remaining <= FeedbackLoop.MAX_VERSION_HISTORY, (
            f"预期最多 {FeedbackLoop.MAX_VERSION_HISTORY} 个版本, 实际 {remaining}"
        )

        # 验证最旧版本 (sample_count 最小) 已被清理
        all_snapshots: list[ModelWeightSnapshot] = (
            db_session.query(ModelWeightSnapshot)
            .order_by(ModelWeightSnapshot.sample_count.asc())
            .all()
        )
        # 最小的 sample_count 应 > 5 (前 5 个被清理)
        assert all_snapshots[0].sample_count > 5, (
            f"最旧版本 sample_count={all_snapshots[0].sample_count}, "
            f"预期 > 5 (前 5 个应被清理)"
        )


# ─── Tests: recalculate_if_needed ──────────────────────────────────────


class TestRecalculateIfNeeded:
    """recalculate_if_needed 完整链路测试"""

    def test_recalculate_if_needed(self, db_session: Session) -> None:
        """完整链路: 检查→收集→优化→保存"""
        # 创建足够的 RiskAssessment 和 PredictionOutcome
        for i in range(FeedbackLoop.MIN_SAMPLES_FOR_RECALC):
            _create_risk_assessment(db_session, ecr_id=100 + i)
            _create_outcome(
                db_session,
                ecr_id=100 + i,
                actual_outcome="approved" if i % 2 == 0 else "rejected",
            )

        snapshot = FeedbackLoop.recalculate_if_needed(db_session)

        assert snapshot is not None
        assert snapshot.version_id is not None
        # 验证 UUID 格式
        uuid.UUID(snapshot.version_id)
        assert snapshot.is_active == 1
        assert snapshot.sample_count == FeedbackLoop.MIN_SAMPLES_FOR_RECALC
        assert snapshot.weights is not None

        # 验证所有权重均在合法范围
        for dim_key, w in snapshot.weights.items():
            assert 0.05 <= float(w) <= 0.50, (
                f"权重 {dim_key}={w} 超出 [0.05, 0.50] 范围"
            )

        # 再调用一次: 新样本数为 0, 不应触发重算
        result = FeedbackLoop.recalculate_if_needed(db_session)
        assert result is None


# ─── Tests: get_active_weights ─────────────────────────────────────────


class TestGetActiveWeights:
    """get_active_weights 方法测试"""

    def test_get_active_weights_default(self, db_session: Session) -> None:
        """无活跃版本时返回 RiskEngine.WEIGHTS"""
        weights: dict[str, float] = FeedbackLoop.get_active_weights(db_session)
        assert weights == RiskEngine.WEIGHTS

    def test_get_active_weights_with_snapshot(self, db_session: Session) -> None:
        """有活跃快照时返回对应权重"""
        custom_weights: dict[str, float] = {
            "bom_impact": 0.25,
            "cert_impact": 0.25,
            "proto_instability": 0.20,
            "cost_overrun": 0.20,
            "hist_failure_rate": 0.10,
        }
        FeedbackLoop.save_version_snapshot(
            db_session,
            weights=custom_weights,
            sample_count=5,
        )

        active_weights: dict[str, float] = FeedbackLoop.get_active_weights(
            db_session,
        )
        assert active_weights == custom_weights


# ─── Tests: rollback_to_version ────────────────────────────────────────


class TestRollbackToVersion:
    """rollback_to_version 方法测试"""

    def test_rollback_to_version(self, db_session: Session) -> None:
        """回滚到指定版本"""
        weights_v1: dict[str, float] = dict(RiskEngine.WEIGHTS)
        v1 = FeedbackLoop.save_version_snapshot(
            db_session,
            weights=weights_v1,
            sample_count=10,
        )

        weights_v2: dict[str, float] = {
            "bom_impact": 0.35,
            "cert_impact": 0.15,
            "proto_instability": 0.20,
            "cost_overrun": 0.15,
            "hist_failure_rate": 0.15,
        }
        FeedbackLoop.save_version_snapshot(
            db_session,
            weights=weights_v2,
            sample_count=20,
        )

        # 当前活跃的是 v2
        assert FeedbackLoop.get_active_weights(db_session) == weights_v2

        # 回滚到 v1
        restored = FeedbackLoop.rollback_to_version(db_session, v1.version_id)
        assert restored.version_id == v1.version_id
        assert restored.is_active == 1

        # 验证当前活跃权重已变回 v1
        active_weights: dict[str, float] = FeedbackLoop.get_active_weights(
            db_session,
        )
        assert active_weights == weights_v1

    def test_rollback_to_version_not_found(self, db_session: Session) -> None:
        """版本不存在抛 ValueError"""
        with pytest.raises(ValueError, match="不存在"):
            FeedbackLoop.rollback_to_version(
                db_session,
                version_id="non-existent-uuid-1234",
            )
