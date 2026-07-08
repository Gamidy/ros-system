"""M3 Approval Advisor — 审批推荐引擎

职责严格限定为：
  ✅ 输入 M1 的 risk_score → 输出推荐动作
  ✅ 输入 M2 的 impact_graph（可选）→ 丰富推荐理由
  ✅ 4个推荐区间: AUTO_APPROVE / FAST_TRACK / FULL_APPROVAL / REJECT_REDESIGN
  ✅ LLM 路径生成可解释性文本
  ✅ LLM 失败时降级到规则路径
  ❌ 不修改 ECR/ECO 状态
  ❌ 不是审批执行系统

全类型注解，无 Any。
"""

import json
import logging
from typing import Optional

from app.schemas.ci_v2 import (
    ApprovalAdvisorAction,
    ApprovalRecommendation,
    ImpactGraphOut,
)

logger = logging.getLogger(__name__)


class ApprovalAdvisor:
    """
    智能审批推荐引擎

    推荐逻辑（规则+LLM混合）:
      risk < 30  → AUTO_APPROVE
      30 ≤ risk < 60 → FAST_TRACK
      60 ≤ risk < 85 → FULL_APPROVAL
      risk ≥ 85 → REJECT_REDESIGN

    LLM 路径: 调用 ai_chat() 生成可解释文本和置信度
    Fast Path: LLM 失败时降级到纯规则
    """

    # 风险阈值常量
    LOW_THRESHOLD: int = 30
    MEDIUM_THRESHOLD: int = 60
    HIGH_THRESHOLD: int = 85

    # 推荐动作映射
    RECOMMENDATION_MAP: dict[str, ApprovalAdvisorAction] = {
        "LOW": ApprovalAdvisorAction.AUTO_APPROVE,
        "MEDIUM": ApprovalAdvisorAction.FAST_TRACK,
        "HIGH": ApprovalAdvisorAction.FULL_APPROVAL,
        "CRITICAL": ApprovalAdvisorAction.REJECT_REDESIGN,
    }

    # 推荐审批人映射
    APPROVER_MAP: dict[str, list[str]] = {
        "LOW": [],
        "MEDIUM": ["module_manager"],
        "HIGH": ["module_manager", "r_and_d_director", "quality_engineer"],
        "CRITICAL": ["module_manager", "r_and_d_director", "quality_engineer"],
    }

    @staticmethod
    def recommend(
        risk_score: float,
        risk_level: str,
        impact_graph: Optional[ImpactGraphOut] = None,
        use_llm: bool = True,
    ) -> ApprovalRecommendation:
        """
        核心推荐方法

        1. 根据 risk_level 确定推荐动作
        2. 尝试 LLM 路径生成可解释文本和置信度
        3. LLM 失败则使用规则路径
        4. 返回 ApprovalRecommendation

        Args:
            risk_score: M1 风险评分 (0-100)
            risk_level: M1 风险等级 (LOW/MEDIUM/HIGH/CRITICAL)
            impact_graph: M2 变更影响图（可选，用于丰富推荐理由）
            use_llm: 是否尝试 LLM 路径

        Returns:
            ApprovalRecommendation
        """
        if use_llm:
            llm_result = ApprovalAdvisor._llm_recommend(
                risk_score=risk_score,
                risk_level=risk_level,
                impact_graph=impact_graph,
            )
            if llm_result is not None:
                recommendation = ApprovalAdvisor.RECOMMENDATION_MAP.get(
                    risk_level,
                    ApprovalAdvisorAction.FULL_APPROVAL,
                )
                required_approvers = ApprovalAdvisor.APPROVER_MAP.get(
                    risk_level,
                    [],
                )
                return ApprovalRecommendation(
                    recommendation=recommendation,
                    required_approvers=required_approvers,
                    reason=llm_result.get("reason", ""),
                    confidence=llm_result.get("confidence", 0.0),
                    risk_level=risk_level,
                    risk_score=risk_score,
                )

        # LLM 失败或 use_llm=False → 降级到规则路径
        return ApprovalAdvisor._rule_based_recommend(
            risk_score=risk_score,
            risk_level=risk_level,
            impact_graph=impact_graph,
        )

    @staticmethod
    def _rule_based_recommend(
        risk_score: float,
        risk_level: str,
        impact_graph: Optional[ImpactGraphOut] = None,
    ) -> ApprovalRecommendation:
        """纯规则推荐（Fast Path / Fallback）"""
        recommendation = ApprovalAdvisor.RECOMMENDATION_MAP.get(
            risk_level,
            ApprovalAdvisorAction.FULL_APPROVAL,
        )
        required_approvers = ApprovalAdvisor.APPROVER_MAP.get(
            risk_level,
            [],
        )

        # 生成规则理由
        reason = ApprovalAdvisor._generate_rule_reason(
            risk_score=risk_score,
            risk_level=risk_level,
            recommendation=recommendation,
            impact_graph=impact_graph,
        )

        # 规则路径置信度固定为 1.0（确定性）
        confidence = 1.0

        return ApprovalRecommendation(
            recommendation=recommendation,
            required_approvers=required_approvers,
            reason=reason,
            confidence=confidence,
            risk_level=risk_level,
            risk_score=risk_score,
        )

    @staticmethod
    def _generate_rule_reason(
        risk_score: float,
        risk_level: str,
        recommendation: ApprovalAdvisorAction,
        impact_graph: Optional[ImpactGraphOut] = None,
    ) -> str:
        """生成规则路径的推荐理由"""
        parts: list[str] = []

        # 风险描述
        level_labels: dict[str, str] = {
            "LOW": "低风险",
            "MEDIUM": "中等风险",
            "HIGH": "高风险",
            "CRITICAL": "极高风险",
        }
        label = level_labels.get(risk_level, risk_level)
        parts.append(f"风险评分 {risk_score:.1f}（{label}）")

        # 推荐动作描述
        action_labels: dict[ApprovalAdvisorAction, str] = {
            ApprovalAdvisorAction.AUTO_APPROVE: "建议自动审批通过",
            ApprovalAdvisorAction.FAST_TRACK: "建议加速审批",
            ApprovalAdvisorAction.FULL_APPROVAL: "建议完整审批",
            ApprovalAdvisorAction.REJECT_REDESIGN: "建议驳回并要求重新设计",
        }
        action_label = action_labels.get(recommendation, str(recommendation))
        parts.append(f"推荐动作: {action_label}")

        # 如有 impact_graph 则补充变更影响信息
        if impact_graph is not None:
            parts.append(
                f"变更影响图包含 {impact_graph.node_count} 个节点、"
                f"{impact_graph.edge_count} 条边，"
                f"ripple score: {impact_graph.ripple_score:.2f}"
            )

        return " | ".join(parts)

    @staticmethod
    def _llm_recommend(
        risk_score: float,
        risk_level: str,
        impact_graph: Optional[ImpactGraphOut] = None,
    ) -> Optional[dict]:
        """LLM 推荐（可解释路径）

        调用 ai_chat() 获取推荐理由和置信度。
        返回 dict 或 None（调用失败时）。

        返回 dict 结构:
            {"reason": str, "confidence": float}

        confidence: 0-1 之间的浮点数
        """
        import asyncio

        try:
            from app.services.ai import ai_chat

            context = ApprovalAdvisor._format_risk_context(
                risk_score=risk_score,
                risk_level=risk_level,
                impact_graph=impact_graph,
            )

            system_prompt = (
                "你是一个研发变更管理的审批推荐助手。根据ECR风险评分和风险等级，"
                "生成审批推荐理由和置信度。输出必须是 JSON 格式，"
                "包含 reason（字符串）和 confidence（0-1之间的浮点数）两个字段。"
            )

            # 尝试获取 API key
            api_key: Optional[str] = None
            try:
                from app.core.config import settings
                api_key = getattr(settings, "AI_API_KEY", None) or getattr(settings, "DEEPSEEK_API_KEY", None)
            except Exception as e:
                logger.warning("获取 settings API key 失败: %s", e)

            if not api_key:
                logger.warning("未配置 AI API key，跳过 LLM 推荐路径")
                return None

            # 在新的事件循环中执行 async 调用
            result = asyncio.run(
                ai_chat(
                    provider="deepseek",
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context},
                    ],
                    api_key=api_key,
                    temperature=0.3,
                    max_tokens=1024,
                )
            )

            if result is not None and result.success and result.text:
                try:
                    parsed = json.loads(result.text)
                    reason = str(parsed.get("reason", ""))
                    confidence = float(parsed.get("confidence", 0.0))
                    if not reason:
                        logger.warning("LLM 返回空 reason")
                        return None
                    return {
                        "reason": reason,
                        "confidence": max(0.0, min(1.0, confidence)),
                    }
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning("解析 LLM 响应失败: %s", e)
                    return None

            return None

        except RuntimeError:
            # 已有运行中的事件循环（如在异步上下文中调用）
            logger.warning("同步上下文中无法执行异步 ai_chat，降级到规则路径")
            return None
        except Exception as e:
            logger.warning("LLM 推荐失败: %s", e)
            return None

    @staticmethod
    def _format_risk_context(
        risk_score: float,
        risk_level: str,
        impact_graph: Optional[ImpactGraphOut] = None,
    ) -> str:
        """格式化风险上下文供 LLM 使用"""
        level_labels: dict[str, str] = {
            "LOW": "低风险",
            "MEDIUM": "中等风险",
            "HIGH": "高风险",
            "CRITICAL": "极高风险",
        }
        label = level_labels.get(risk_level, risk_level)

        lines: list[str] = [
            f"风险评分: {risk_score:.1f}",
            f"风险等级: {risk_level}（{label}）",
            "",
            "推荐区间说明:",
            "  score < 30  → AUTO_APPROVE（自动审批）",
            "  30 ≤ score < 60 → FAST_TRACK（加速审批）",
            "  60 ≤ score < 85 → FULL_APPROVAL（完整审批）",
            "  score ≥ 85 → REJECT_REDESIGN（驳回并要求重新设计）",
        ]

        if impact_graph is not None:
            lines.append("")
            lines.append("变更影响图信息:")
            lines.append(f"  节点数: {impact_graph.node_count}")
            lines.append(f"  边数: {impact_graph.edge_count}")
            lines.append(f"  Ripple Score: {impact_graph.ripple_score:.2f}")
            lines.append(f"  最大传播深度: {impact_graph.max_depth}")
            if impact_graph.nodes:
                lines.append("  节点列表:")
                for node in impact_graph.nodes[:10]:  # 最多展示10个节点
                    lines.append(
                        f"    - {node.label} (type={node.node_type}, "
                        f"impact={node.impact_score:.2f}, depth={node.depth})"
                    )

        return "\n".join(lines)
