"""M4-T3 Feedback Loop — 预测结果反馈闭环

Prediction → Execution → Outcome → Correction → Model Update

负责:
  - 记录预测结果的实际反馈 (record_outcome)
  - 查询反馈历史 (get_outcomes)
  - 检查是否需要权重重算 (_should_recalculate)
  - 收集训练样本 (_collect_training_samples)
  - 启发式权重优化 (_optimize_weights)
  - 版本快照管理 (save_version_snapshot, rollback_to_version)
  - 公开调用链路 (recalculate_if_needed)

全类型注解，无 Any，无裸 except。
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.ci_v2_feedback import PredictionOutcome, ModelWeightSnapshot
from app.models.ci_v2_risk import RiskAssessment
from app.services.ai.risk_engine import RiskEngine
from app.services.events import EventBus

logger = logging.getLogger(__name__)

# ── 风险等级 → 预测推荐动作映射 ─────────────────────────────────────
# RiskEngine 的 get_mitigation_suggestions 在每个等级末尾追加 RecommendationEnum，
# 这里做等价映射以便持久化 predicted_action。
_RISK_LEVEL_TO_ACTION: dict[str, str] = {
    "LOW": "AUTO_APPROVE",
    "MEDIUM": "FAST_TRACK",
    "HIGH": "FULL_APPROVAL",
    "CRITICAL": "REJECT_REDESIGN",
}


class FeedbackLoop:
    """预测结果反馈闭环 — 收集/权重重算/版本管理

    Prediction → Execution → Outcome → Correction → Model Update

    MIN_SAMPLES_FOR_RECALC : 最小触发权重重算的新样本数
    MAX_VERSION_HISTORY    : 最大保留版本数（超出的最旧版本自动清理）
    """

    MIN_SAMPLES_FOR_RECALC: int = 10
    MAX_VERSION_HISTORY: int = 20

    # ── 反馈记录 ───────────────────────────────────────────────────

    @staticmethod
    def record_outcome(
        db: Session,
        ecr_id: int,
        actual_outcome: str,
        outcome_detail: Optional[dict] = None,
    ) -> PredictionOutcome:
        """记录预测结果反馈

        自动查询该 ECR 最近一次的 RiskAssessment 数据并关联记录。
        查找策略：取该 ECR 下最新（id 最大）的 RiskAssessment 记录。

        Args:
            db:              数据库 Session
            ecr_id:          ECR ID
            actual_outcome:   实际结果（approved/rejected/bom_success/bom_failure/cancelled）
            outcome_detail:   可选的结果详情字典

        Returns:
            已持久化的 PredictionOutcome 对象

        Raises:
            ValueError: 当 ecr_id 不存在对应的 RiskAssessment 时
        """
        # 查询该 ECR 最新的 RiskAssessment
        assessment: Optional[RiskAssessment] = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.ecr_id == ecr_id)
            .order_by(desc(RiskAssessment.id))
            .first()
        )

        if assessment is None:
            raise ValueError(
                f"ECR {ecr_id} 没有关联的 RiskAssessment，无法记录反馈"
            )

        # 根据风险等级推导预测推荐动作
        risk_level_str: str = str(assessment.risk_level)
        predicted_action: Optional[str] = _RISK_LEVEL_TO_ACTION.get(
            risk_level_str
        )

        outcome = PredictionOutcome(
            ecr_id=ecr_id,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            predicted_action=predicted_action,
            actual_outcome=actual_outcome,
            outcome_detail=outcome_detail,
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)

        logger.info(
            "反馈记录已持久化: ecr_id=%s, actual_outcome=%s, outcome_id=%s",
            ecr_id,
            actual_outcome,
            outcome.id,
        )

        # 触发事件（便于其它模块感知反馈闭环）
        try:
            bus = EventBus()
            bus.emit(
                "feedback.outcome_recorded",
                ecr_id=ecr_id,
                outcome_id=outcome.id,
                actual_outcome=actual_outcome,
            )
        except Exception as e:
            logger.warning("反馈事件发送失败（非致命）: %s", e)

        return outcome

    # ── 反馈查询 ───────────────────────────────────────────────────

    @staticmethod
    def get_outcomes(db: Session, ecr_id: int) -> list[PredictionOutcome]:
        """查询某 ECR 的全部反馈历史

        Args:
            db:     数据库 Session
            ecr_id: ECR ID

        Returns:
            按记录时间降序排列的 PredictionOutcome 列表
        """
        return (
            db.query(PredictionOutcome)
            .filter(PredictionOutcome.ecr_id == ecr_id)
            .order_by(desc(PredictionOutcome.recorded_at))
            .all()
        )

    # ── 重算判断 ───────────────────────────────────────────────────

    @staticmethod
    def _should_recalculate(db: Session) -> bool:
        """检查未参与训练的新样本数是否 ≥ MIN_SAMPLES_FOR_RECALC

        逻辑：
          1. 获取当前活跃版本快照的 sample_count（若无快照则为 0）
          2. 统计 PredictionOutcome 总记录数
          3. 若 总记录数 - 已训练数 ≥ MIN_SAMPLES_FOR_RECALC 则返回 True

        Args:
            db: 数据库 Session

        Returns:
            是否需要触发权重重算
        """
        # 获取最新版本的 sample_count
        active_snapshot: Optional[ModelWeightSnapshot] = (
            db.query(ModelWeightSnapshot)
            .filter(ModelWeightSnapshot.is_active == 1)
            .order_by(desc(ModelWeightSnapshot.id))
            .first()
        )

        trained_count: int = int(active_snapshot.sample_count) if active_snapshot else 0

        total_outcomes: int = (
            db.query(func.count(PredictionOutcome.id))
            .scalar()
            or 0
        )

        new_samples: int = total_outcomes - trained_count
        should_run: bool = new_samples >= FeedbackLoop.MIN_SAMPLES_FOR_RECALC

        logger.debug(
            "_should_recalculate: total_outcomes=%s, trained=%s, new=%s, threshold=%s → %s",
            total_outcomes,
            trained_count,
            new_samples,
            FeedbackLoop.MIN_SAMPLES_FOR_RECALC,
            should_run,
        )
        return should_run

    # ── 样本收集 ───────────────────────────────────────────────────

    @staticmethod
    def _collect_training_samples(db: Session) -> list[dict]:
        """收集所有样本用于权重重算

        遍历每条 PredictionOutcome，通过 ecr_id 查找对应的 RiskAssessment，
        从中提取 5 个信号维度分数，与 actual_outcome 一起构成一条样本。

        只包含能找到 RiskAssessment 的有效样本。

        Args:
            db: 数据库 Session

        Returns:
            list[dict]: 每条包含 risk_score, actual_outcome 及5个信号维度分
        """
        outcomes: list[PredictionOutcome] = (
            db.query(PredictionOutcome)
            .order_by(PredictionOutcome.id)
            .all()
        )

        # 批量收集 ecr_id 列表
        ecr_ids: list[int] = list({o.ecr_id for o in outcomes})

        # 一次查询所有相关的 RiskAssessment（取每个 ecr_id 最新的那条）
        assessments_map: dict[int, RiskAssessment] = {}
        for ecr_id_val in ecr_ids:
            assessment: Optional[RiskAssessment] = (
                db.query(RiskAssessment)
                .filter(RiskAssessment.ecr_id == ecr_id_val)
                .order_by(desc(RiskAssessment.id))
                .first()
            )
            if assessment is not None:
                assessments_map[ecr_id_val] = assessment

        samples: list[dict] = []
        for outcome in outcomes:
            assessment = assessments_map.get(outcome.ecr_id)
            if assessment is None:
                logger.debug(
                    "跳过反馈 ecr_id=%s: 无 RiskAssessment", outcome.ecr_id
                )
                continue

            samples.append({
                "ecr_id": outcome.ecr_id,
                "risk_score": float(outcome.risk_score),
                "risk_level": outcome.risk_level,
                "bom_impact": float(assessment.bom_impact or 0),
                "cert_impact": float(assessment.cert_impact or 0),
                "proto_instability": float(assessment.proto_instability or 0),
                "cost_overrun": float(assessment.cost_overrun or 0),
                "hist_failure_rate": float(assessment.hist_failure_rate or 0),
                "actual_outcome": outcome.actual_outcome,
            })

        logger.info("收集到 %s 条有效训练样本", len(samples))
        return samples

    # ── 权重优化（启发式） ──────────────────────────────────────────

    @staticmethod
    def _optimize_weights(
        samples: list[dict],
        current_weights: dict[str, float],
    ) -> dict[str, float]:
        """根据样本优化权重（简单启发式）—— Deterministic

        核心逻辑：
          对每条样本，找出贡献度最高的信号维度。
          - 若结果为 approved/bom_success（成功） → 该维度权重降低 2%
            （说明风险被高估，该维度权重应减少）
          - 若结果为 rejected/bom_failure（失败） → 该维度权重提升 2%
            （说明风险被正确识别，该维度权重应增加）
          - cancelled 样本不参与调整

        边界保护：所有权重 clamped 到 [0.05, 0.50]

        Args:
            samples:        _collect_training_samples 返回的样本列表
            current_weights: 当前权重字典

        Returns:
            优化后的权重字典
        """
        if not samples:
            return dict(current_weights)

        new_weights: dict[str, float] = dict(current_weights)
        dims: list[str] = list(new_weights.keys())

        for sample in samples:
            outcome: str = sample.get("actual_outcome", "")

            # cancelled 不参与调整
            if outcome == "cancelled":
                continue

            is_success: bool = outcome in ("approved", "bom_success")

            # 计算各维度的实际贡献值（score × weight）
            contributions: dict[str, float] = {}
            for dim in dims:
                score: float = sample.get(dim, 0.0)
                contributions[dim] = score * new_weights[dim]

            total_contrib: float = sum(contributions.values())
            if total_contrib <= 0:
                continue

            # 找出贡献度最高的维度
            top_dim: str = max(contributions, key=contributions.get)  # type: ignore[arg-type]
            # top_dim 一定是 dims 中的某个值，安全

            # 仅当该维度贡献占比 > 30% 时才调整（避免微小波动）
            contribution_ratio: float = contributions[top_dim] / total_contrib
            if contribution_ratio <= 0.3:
                continue

            if is_success:
                # 成功样本 → 该维度高估了风险，降低权重
                new_weights[top_dim] *= 0.98
            else:
                # 失败样本 → 该维度正确识别了风险，提高权重
                new_weights[top_dim] *= 1.02

        # 边界保护: [0.05, 0.50]
        for dim in dims:
            w: float = new_weights[dim]
            w = max(0.05, min(0.50, w))
            new_weights[dim] = round(w, 4)

        # 保持总和为 1.0（归一化）
        total: float = sum(new_weights.values())
        if total > 0:
            for dim in dims:
                norm_w: float = new_weights[dim] / total
                norm_w = max(0.05, min(0.50, norm_w))
                new_weights[dim] = round(norm_w, 4)

        logger.info(
            "权重优化完成: %s → %s",
            current_weights,
            new_weights,
        )
        return new_weights

    # ── 版本快照 ───────────────────────────────────────────────────

    @staticmethod
    def save_version_snapshot(
        db: Session,
        weights: dict[str, float],
        sample_count: int,
    ) -> ModelWeightSnapshot:
        """保存新版权重快照

        流程：
          1. 生成 UUID version_id
          2. 取消所有现有快照的活跃标记
          3. 创建新快照并标记为活跃
          4. 自动清理超出 MAX_VERSION_HISTORY 的最旧版本

        Args:
            db:           数据库 Session
            weights:       权重配置字典
            sample_count:  训练样本数

        Returns:
            已持久化的新 ModelWeightSnapshot
        """
        version_id: str = str(uuid.uuid4())

        # 取消所有旧活跃标记
        active_snapshots: list[ModelWeightSnapshot] = (
            db.query(ModelWeightSnapshot)
            .filter(ModelWeightSnapshot.is_active == 1)
            .all()
        )
        for snap in active_snapshots:
            snap.is_active = 0

        # 创建新快照
        snapshot = ModelWeightSnapshot(
            version_id=version_id,
            weights=weights,
            sample_count=sample_count,
            is_active=1,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        logger.info(
            "新版本快照已保存: version_id=%s, sample_count=%s, weights=%s",
            version_id,
            sample_count,
            weights,
        )

        # 自动清理超出 MAX_VERSION_HISTORY 的旧版本
        FeedbackLoop._cleanup_old_versions(db)

        return snapshot

    @staticmethod
    def _cleanup_old_versions(db: Session) -> None:
        """清理超出 MAX_VERSION_HISTORY 的最旧版本（非活跃）"""
        total: int = (
            db.query(func.count(ModelWeightSnapshot.id))
            .scalar()
            or 0
        )

        if total <= FeedbackLoop.MAX_VERSION_HISTORY:
            return

        excess: int = total - FeedbackLoop.MAX_VERSION_HISTORY

        # 按 created_at 升序取最旧的 excess 条
        old_versions: list[ModelWeightSnapshot] = (
            db.query(ModelWeightSnapshot)
            .order_by(ModelWeightSnapshot.created_at.asc())
            .limit(excess)
            .all()
        )

        for old in old_versions:
            if old.is_active == 1:
                # 保护当前活跃版本不被删除
                continue
            db.delete(old)

        db.commit()
        logger.info(
            "已清理 %s 个旧版本快照（保留最近 %s 个）",
            excess,
            FeedbackLoop.MAX_VERSION_HISTORY,
        )

    # ── 公开方法 ───────────────────────────────────────────────────

    @staticmethod
    def recalculate_if_needed(
        db: Session,
    ) -> Optional[ModelWeightSnapshot]:
        """公开方法：检查→收集→优化→保存（一次完整链路）

        步骤：
          1. _should_recalculate — 判断是否需要重算
          2. _collect_training_samples — 收集样本
          3. 获取当前活跃权重（若无则用 RiskEngine.WEIGHTS）
          4. _optimize_weights — 启发式优化
          5. save_version_snapshot — 保存新版本

        Returns:
            若触发了重算则返回新 ModelWeightSnapshot，否则返回 None
        """
        if not FeedbackLoop._should_recalculate(db):
            logger.info("无需权重重算: 新样本数不足 %s", FeedbackLoop.MIN_SAMPLES_FOR_RECALC)
            return None

        samples: list[dict] = FeedbackLoop._collect_training_samples(db)
        if not samples:
            logger.warning("权重重算中止: 无有效样本")
            return None

        current_weights: dict[str, float] = FeedbackLoop.get_active_weights(db)
        optimized: dict[str, float] = FeedbackLoop._optimize_weights(samples, current_weights)

        snapshot: ModelWeightSnapshot = FeedbackLoop.save_version_snapshot(
            db,
            weights=optimized,
            sample_count=len(samples),
        )

        logger.info(
            "权重重算完成: version_id=%s, sample_count=%s",
            snapshot.version_id,
            snapshot.sample_count,
        )

        # 触发事件
        try:
            bus = EventBus()
            bus.emit(
                "feedback.weights_updated",
                version_id=snapshot.version_id,
                sample_count=snapshot.sample_count,
                weights=snapshot.weights,
            )
        except Exception as e:
            logger.warning("权重重算事件发送失败（非致命）: %s", e)

        return snapshot

    @staticmethod
    def get_active_weights(db: Session) -> dict[str, float]:
        """获取当前活跃权重

        查询活跃的 ModelWeightSnapshot，若不存在则返回 RiskEngine.WEIGHTS 的副本。
        返回值始终是 str→float 字典。

        Args:
            db: 数据库 Session

        Returns:
            当前权重配置字典
        """
        active: Optional[ModelWeightSnapshot] = (
            db.query(ModelWeightSnapshot)
            .filter(ModelWeightSnapshot.is_active == 1)
            .order_by(desc(ModelWeightSnapshot.id))
            .first()
        )

        if active is not None and active.weights is not None:
            return {str(k): float(v) for k, v in active.weights.items()}

        # 无活跃版本 → 返回默认权重副本
        return dict(RiskEngine.WEIGHTS)

    @staticmethod
    def rollback_to_version(
        db: Session,
        version_id: str,
    ) -> ModelWeightSnapshot:
        """回滚到指定版本

        将指定 version_id 的快照标记为活跃，并取消当前活跃标记。

        Args:
            db:         数据库 Session
            version_id: 目标版本的 UUID 字符串

        Returns:
            被激活的 ModelWeightSnapshot

        Raises:
            ValueError: 当 version_id 不存在时
        """
        target: Optional[ModelWeightSnapshot] = (
            db.query(ModelWeightSnapshot)
            .filter(ModelWeightSnapshot.version_id == version_id)
            .first()
        )

        if target is None:
            raise ValueError(
                f"version_id '{version_id}' 不存在，无法回滚"
            )

        # 取消所有旧活跃标记
        active_snapshots: list[ModelWeightSnapshot] = (
            db.query(ModelWeightSnapshot)
            .filter(ModelWeightSnapshot.is_active == 1)
            .all()
        )
        for snap in active_snapshots:
            snap.is_active = 0

        # 激活目标版本
        target.is_active = 1
        db.commit()
        db.refresh(target)

        logger.info(
            "已回滚到版本: version_id=%s, sample_count=%s, weights=%s",
            version_id,
            target.sample_count,
            target.weights,
        )

        return target
