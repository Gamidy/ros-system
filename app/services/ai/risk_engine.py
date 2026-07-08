"""M1 Risk Engine — AI变更预测引擎（纯风险评分计算器）

职责严格限定为：
  ✅ 输入信号 → 计算风险分数 → 输出风险等级
  ❌ 不做审批决策
  ❌ 不做UI逻辑
  ❌ 不依赖前端
  ❌ 不依赖外部AI/LLM

RiskEngine.calculate() 是纯函数（确定性的，相同输入=相同输出）。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ci_v2_risk import RiskAssessment
from app.models.ecr_eco import ECRRequest, ECO, ECOItem
from app.schemas.ci_v2 import (
    RiskAssessmentOut,
    RiskLevelEnum,
    RecommendationEnum,
    SignalInput,
)

logger = logging.getLogger(__name__)

# 等级分界线（左闭右开）
_LOW_MAX = 30.0
_MEDIUM_MAX = 60.0
_HIGH_MAX = 85.0


class RiskEngine:
    """风险引擎 — 确定性信号评分计算器

    权重配置（可调，但运行时视为常量）：
      bom_impact         0.3
      cert_impact        0.2
      proto_instability  0.2
      cost_overrun       0.2
      hist_failure_rate  0.1
    """

    WEIGHTS: dict[str, float] = {
        "bom_impact": 0.3,
        "cert_impact": 0.2,
        "proto_instability": 0.2,
        "cost_overrun": 0.2,
        "hist_failure_rate": 0.1,
    }

    # ── 核心评分 ─────────────────────────────────────────────────────

    @staticmethod
    def calculate(signals: SignalInput) -> RiskAssessmentOut:
        """核心评分计算器

        - 确定性函数：相同输入 = 相同输出
        - 无外部依赖
        - 输入缺失时优雅降级（默认为0）
        """
        risk_score = (
            signals.bom_impact * RiskEngine.WEIGHTS["bom_impact"]
            + signals.cert_impact * RiskEngine.WEIGHTS["cert_impact"]
            + signals.proto_instability * RiskEngine.WEIGHTS["proto_instability"]
            + signals.cost_overrun * RiskEngine.WEIGHTS["cost_overrun"]
            + signals.hist_failure_rate * RiskEngine.WEIGHTS["hist_failure_rate"]
        )

        level = RiskEngine._score_to_level(risk_score)
        risk_vector = RiskEngine.get_risk_vector(signals)
        mitigation = RiskEngine.get_mitigation_suggestions(level, risk_vector)

        # 构造临时输出对象（id/ecr_id/created_at 在持久化后填充）
        return RiskAssessmentOut(
            id=0,
            ecr_id=0,
            risk_score=round(risk_score, 2),
            risk_level=level,
            bom_impact=signals.bom_impact,
            cert_impact=signals.cert_impact,
            proto_instability=signals.proto_instability,
            cost_overrun=signals.cost_overrun,
            hist_failure_rate=signals.hist_failure_rate,
            signal_details=risk_vector,
            mitigation_suggestions=mitigation,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _score_to_level(score: float) -> RiskLevelEnum:
        """将数值分数映射为风险等级"""
        if score < _LOW_MAX:
            return RiskLevelEnum.LOW
        if score < _MEDIUM_MAX:
            return RiskLevelEnum.MEDIUM
        if score < _HIGH_MAX:
            return RiskLevelEnum.HIGH
        return RiskLevelEnum.CRITICAL

    # ── 风险向量 ─────────────────────────────────────────────────────

    @staticmethod
    def get_risk_vector(signals: SignalInput) -> dict:
        """返回4维风险向量（按等级分类聚合）

        将每个信号维度按其对总分级的贡献映射到4个风险桶。
        """
        weights = RiskEngine.WEIGHTS

        # 每个维度的实际分数贡献
        contributions: dict[str, float] = {
            "bom_impact": signals.bom_impact * weights["bom_impact"],
            "cert_impact": signals.cert_impact * weights["cert_impact"],
            "proto_instability": signals.proto_instability * weights["proto_instability"],
            "cost_overrun": signals.cost_overrun * weights["cost_overrun"],
            "hist_failure_rate": signals.hist_failure_rate * weights["hist_failure_rate"],
        }

        total = sum(contributions.values())

        # 按等级聚合贡献
        low_contrib = 0.0
        medium_contrib = 0.0
        high_contrib = 0.0
        critical_contrib = 0.0

        sig_map: dict[str, float] = {
            "bom_impact": signals.bom_impact,
            "cert_impact": signals.cert_impact,
            "proto_instability": signals.proto_instability,
            "cost_overrun": signals.cost_overrun,
            "hist_failure_rate": signals.hist_failure_rate,
        }

        for dim_name, raw_score in sig_map.items():
            contrib = contributions[dim_name]
            if raw_score < _LOW_MAX:
                low_contrib += contrib
            elif raw_score < _MEDIUM_MAX:
                medium_contrib += contrib
            elif raw_score < _HIGH_MAX:
                high_contrib += contrib
            else:
                critical_contrib += contrib

        return {
            "total_score": round(total, 2),
            "contributions": {k: round(v, 2) for k, v in contributions.items()},
            "risk_buckets": {
                "low": round(low_contrib, 2),
                "medium": round(medium_contrib, 2),
                "high": round(high_contrib, 2),
                "critical": round(critical_contrib, 2),
            },
        }

    # ── 缓解建议 ─────────────────────────────────────────────────────

    @staticmethod
    def get_mitigation_suggestions(
        risk_level: RiskLevelEnum,
        risk_vector: dict,
    ) -> list[str]:
        """根据风险等级返回缓解建议"""
        suggestions: list[str] = []
        buckets = risk_vector.get("risk_buckets", {})

        if risk_level == RiskLevelEnum.LOW:
            suggestions.append("风险极低，可按常规流程快速审批。")
            suggestions.append("建议保留当前方案，无需额外缓解措施。")
            suggestions.append(RecommendationEnum.AUTO_APPROVE.value)

        elif risk_level == RiskLevelEnum.MEDIUM:
            suggestions.append("中等风险，建议加速审批流程（Fast-Track）。")
            suggestions.append("建议安排领域专家进行针对性的评审。")
            if buckets.get("bom_impact", 0) > 10:
                suggestions.append("BOM影响较高，建议提前准备物料备选方案。")
            if buckets.get("cert_impact", 0) > 10:
                suggestions.append("认证影响显著，建议提前启动认证预审。")
            suggestions.append(RecommendationEnum.FAST_TRACK.value)

        elif risk_level == RiskLevelEnum.HIGH:
            suggestions.append("高风险，必须进行完整审批流程（Full Approval）。")
            suggestions.append("建议组织跨部门评审会议，包含质量、工程、采购。")
            suggestions.append("建议制定详细的风险缓释计划并指定责任人。")
            if buckets.get("cost_overrun", 0) > 15:
                suggestions.append("成本超支风险突出，需财务部门介入审核。")
            if buckets.get("hist_failure_rate", 0) > 8:
                suggestions.append("历史故障率较高，建议增加验证测试范围。")
            suggestions.append(RecommendationEnum.FULL_APPROVAL.value)

        elif risk_level == RiskLevelEnum.CRITICAL:
            suggestions.append("⚠️ CRITICAL — 极高风险！建议重新设计方案（Redesign）。")
            suggestions.append("建议立即暂停当前变更，重新评估技术路线。")
            suggestions.append("建议召集技术委员会专题会议，审查根本原因。")
            suggestions.append("在风险降至HIGH以下前，不建议继续推进。")
            suggestions.append(RecommendationEnum.REJECT_REDESIGN.value)

        return suggestions

    # ── ECR 关联评估 ─────────────────────────────────────────────────

    def assess_for_ecr(
        self,
        db: Session,
        ecr_id: int,
    ) -> Optional[RiskAssessmentOut]:
        """从ECR的关联数据收集信号并评估

        流程：
          1. 查询 ECR 及其关联的 ECO / ECOItem
          2. 根据数据计算5个维度信号值
          3. 调用 calculate() 获取评分结果
          4. 持久化 RiskAssessment 到数据库
          5. 返回完整结果
        """
        ecr = db.query(ECRRequest).filter(ECRRequest.id == ecr_id).first()
        if ecr is None:
            logger.warning("ECR %s not found, cannot assess risk", ecr_id)
            return None

        signals = self._collect_signals(db, ecr)
        result = self.calculate(signals)

        # 持久化
        assessment = RiskAssessment(
            ecr_id=ecr_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level.value,
            bom_impact=result.bom_impact,
            cert_impact=result.cert_impact,
            proto_instability=result.proto_instability,
            cost_overrun=result.cost_overrun,
            hist_failure_rate=result.hist_failure_rate,
            signal_details=result.signal_details,
            mitigation_suggestions=result.mitigation_suggestions,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # 用数据库实际数据覆盖输出
        result.id = assessment.id
        result.ecr_id = assessment.ecr_id
        result.created_at = assessment.created_at

        return result

    @staticmethod
    def _collect_signals(db: Session, ecr: ECRRequest) -> SignalInput:
        """从 ECR / ECO / ECOItem 收集并计算5个维度信号值

        启发式估算（实际业务可按需调优）：
          bom_impact:        ECOItem 中 change_type 为 BOM 相关条目比例 * 100
          cert_impact:       ECR 的 affected_documents / description 含认证关键词
          proto_instability: ECOItem 数量超过阈值则升高
          cost_overrun:      ECR 紧急度映射
          hist_failure_rate: 默认低值
        """
        # 获取关联的 ECO
        eco: Optional[ECO] = (
            db.query(ECO).filter(ECO.ecr_id == ecr.id).first()
        )

        bom_impact = 0.0
        proto_instability = 0.0
        cert_impact = 0.0
        cost_overrun = 0.0
        hist_failure_rate = 5.0  # 基础默认值

        if eco is not None:
            items: list[ECOItem] = (
                db.query(ECOItem)
                .filter(ECOItem.eco_id == eco.id)
                .all()
            )
            total_items = len(items)
            if total_items > 0:
                # BOM impact: 变更类型含 BOM 相关关键词的比例
                bom_change_types = {"bom", "bom_item", "part", "material"}
                bom_count = sum(
                    1 for it in items
                    if it.change_type is not None
                    and it.change_type.lower() in bom_change_types
                )
                bom_impact = round((bom_count / total_items) * 100, 2)

                # Proto instability: 大量条目意味着方案不稳定
                instability_factor = min(total_items / 10.0, 1.0)
                proto_instability = round(instability_factor * 60, 2)

        # Cert impact: 从 ECR 描述和 affected_documents 中检测认证关键词
        cert_keywords = {"cert", "认证", "ce", "cb", "ul", "ccc", "safety", "安规", "emc"}
        cert_hit = 0.0
        if ecr.description is not None:
            desc_lower = ecr.description.lower()
            for kw in cert_keywords:
                if kw in desc_lower:
                    cert_hit += 1.0
        if ecr.affected_documents is not None:
            docs_str = str(ecr.affected_documents).lower()
            for kw in cert_keywords:
                if kw in docs_str:
                    cert_hit += 0.5
        cert_impact = round(min(cert_hit * 15.0, 100.0), 2)

        # Cost overrun: 根据紧急度映射
        urgency_map: dict[str, float] = {
            "urgent": 70.0,
            "high": 50.0,
            "medium": 30.0,
            "low": 10.0,
        }
        urgency_val = ecr.urgency
        if urgency_val is not None:
            cost_overrun = urgency_map.get(urgency_val.lower(), 20.0)
        else:
            cost_overrun = 20.0

        return SignalInput(
            bom_impact=bom_impact,
            cert_impact=cert_impact,
            proto_instability=proto_instability,
            cost_overrun=cost_overrun,
            hist_failure_rate=hist_failure_rate,
        )


# ── 顶层快捷函数 ─────────────────────────────────────────────────────

def calculate_risk(signals: SignalInput) -> RiskAssessmentOut:
    """快捷函数 — 无需创建引擎实例即可计算风险"""
    return RiskEngine.calculate(signals)
