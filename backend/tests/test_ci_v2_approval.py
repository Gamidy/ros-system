"""M3 Approval Advisor — 单元测试

验收标准：
  1. 4个风险区间返回正确的推荐动作
  2. 边界值精确（30/60/85）
  3. LLM 失败时优雅降级到规则路径（非崩溃）
  4. 推荐结果可序列化为 ApprovalRecommendation Schema
  5. approval_advisor.py 中不修改任何 ECR/ECO 状态
  6. pytest 全部通过
  7. 全类型注解，无 Any
"""

import pytest

from app.schemas.ci_v2 import (
    ApprovalAdvisorAction,
    ApprovalRecommendation,
    ImpactGraphOut,
    ImpactNode,
    ImpactEdge,
)
from app.services.ai.approval_advisor import ApprovalAdvisor


class TestApprovalAdvisorRecommend:
    """ApprovalAdvisor.recommend() 单元测试"""

    def test_auto_approve(self) -> None:
        """risk=20, level=LOW → AUTO_APPROVE"""
        result = ApprovalAdvisor.recommend(
            risk_score=20.0,
            risk_level="LOW",
            use_llm=False,
        )
        assert result.recommendation == ApprovalAdvisorAction.AUTO_APPROVE
        assert result.risk_level == "LOW"
        assert result.risk_score == 20.0
        assert result.required_approvers == []

    def test_fast_track(self) -> None:
        """risk=45, level=MEDIUM → FAST_TRACK"""
        result = ApprovalAdvisor.recommend(
            risk_score=45.0,
            risk_level="MEDIUM",
            use_llm=False,
        )
        assert result.recommendation == ApprovalAdvisorAction.FAST_TRACK
        assert result.risk_level == "MEDIUM"
        assert result.risk_score == 45.0

    def test_full_approval(self) -> None:
        """risk=70, level=HIGH → FULL_APPROVAL"""
        result = ApprovalAdvisor.recommend(
            risk_score=70.0,
            risk_level="HIGH",
            use_llm=False,
        )
        assert result.recommendation == ApprovalAdvisorAction.FULL_APPROVAL
        assert result.risk_level == "HIGH"
        assert result.risk_score == 70.0

    def test_reject_redesign(self) -> None:
        """risk=90, level=CRITICAL → REJECT_REDESIGN"""
        result = ApprovalAdvisor.recommend(
            risk_score=90.0,
            risk_level="CRITICAL",
            use_llm=False,
        )
        assert result.recommendation == ApprovalAdvisorAction.REJECT_REDESIGN
        assert result.risk_level == "CRITICAL"
        assert result.risk_score == 90.0

    # ── 边界值测试 ──────────────────────────────────────────────────────

    def test_boundary_values(self) -> None:
        """边界值：29.9/30/59.9/60/84.9/85 → 正确区间"""
        # 29.9 → LOW → AUTO_APPROVE
        r1 = ApprovalAdvisor.recommend(29.9, "LOW", use_llm=False)
        assert r1.recommendation == ApprovalAdvisorAction.AUTO_APPROVE
        assert r1.risk_score == 29.9

        # 30.0 → MEDIUM → FAST_TRACK
        r2 = ApprovalAdvisor.recommend(30.0, "MEDIUM", use_llm=False)
        assert r2.recommendation == ApprovalAdvisorAction.FAST_TRACK
        assert r2.risk_score == 30.0

        # 59.9 → MEDIUM → FAST_TRACK
        r3 = ApprovalAdvisor.recommend(59.9, "MEDIUM", use_llm=False)
        assert r3.recommendation == ApprovalAdvisorAction.FAST_TRACK
        assert r3.risk_score == 59.9

        # 60.0 → HIGH → FULL_APPROVAL
        r4 = ApprovalAdvisor.recommend(60.0, "HIGH", use_llm=False)
        assert r4.recommendation == ApprovalAdvisorAction.FULL_APPROVAL
        assert r4.risk_score == 60.0

        # 84.9 → HIGH → FULL_APPROVAL
        r5 = ApprovalAdvisor.recommend(84.9, "HIGH", use_llm=False)
        assert r5.recommendation == ApprovalAdvisorAction.FULL_APPROVAL
        assert r5.risk_score == 84.9

        # 85.0 → CRITICAL → REJECT_REDESIGN
        r6 = ApprovalAdvisor.recommend(85.0, "CRITICAL", use_llm=False)
        assert r6.recommendation == ApprovalAdvisorAction.REJECT_REDESIGN
        assert r6.risk_score == 85.0

    # ── 降级测试 ────────────────────────────────────────────────────────

    def test_rule_based_fallback(self) -> None:
        """use_llm=False 时走规则路径"""
        result = ApprovalAdvisor.recommend(
            risk_score=45.0,
            risk_level="MEDIUM",
            use_llm=False,
        )
        assert result.recommendation == ApprovalAdvisorAction.FAST_TRACK
        # 规则路径置信度固定为 1.0
        assert result.confidence == 1.0
        # 理由应包含风险描述
        assert "风险评分" in result.reason

    def test_llm_fallback(self, mocker) -> None:
        """LLM 返回 None 时优雅降级到规则路径"""
        # 模拟 _llm_recommend 返回 None（模拟 LLM 调用失败）
        mocker.patch.object(
            ApprovalAdvisor,
            "_llm_recommend",
            return_value=None,
        )

        result = ApprovalAdvisor.recommend(
            risk_score=70.0,
            risk_level="HIGH",
            use_llm=True,
        )

        # 应降级到规则路径
        assert result.recommendation == ApprovalAdvisorAction.FULL_APPROVAL
        assert result.confidence == 1.0
        assert "高风险" in result.reason

    # ── Impact Graph 测试 ──────────────────────────────────────────────

    def test_recommend_with_impact_graph(self) -> None:
        """传入 impact_graph 增强推荐理由"""
        graph = ImpactGraphOut(
            nodes=[
                ImpactNode(
                    id="eco_1",
                    node_type="eco",
                    label="ECO: ECO-001",
                    impact_score=0.7,
                    affected_objects=[{"id": 1}],
                    depth=1,
                ),
            ],
            edges=[
                ImpactEdge(
                    source_id="ecr_1",
                    target_id="eco_1",
                    weight=1.0,
                    label="ECR → ECO",
                ),
            ],
            ripple_score=35.0,
            max_depth=1,
            node_count=1,
            edge_count=1,
        )

        result = ApprovalAdvisor.recommend(
            risk_score=45.0,
            risk_level="MEDIUM",
            impact_graph=graph,
            use_llm=False,
        )

        assert result.recommendation == ApprovalAdvisorAction.FAST_TRACK
        # 理由应包含 impact_graph 信息
        assert "变更影响图" in result.reason
        assert "1 个节点" in result.reason

    # ── 审批人映射测试 ──────────────────────────────────────────────────

    def test_approver_mapping(self) -> None:
        """正确返回各风险等级的审批人列表"""
        # LOW → 无审批人
        r1 = ApprovalAdvisor.recommend(20.0, "LOW", use_llm=False)
        assert r1.required_approvers == []

        # MEDIUM → module_manager
        r2 = ApprovalAdvisor.recommend(45.0, "MEDIUM", use_llm=False)
        assert r2.required_approvers == ["module_manager"]

        # HIGH → module_manager, r_and_d_director, quality_engineer
        r3 = ApprovalAdvisor.recommend(70.0, "HIGH", use_llm=False)
        assert r3.required_approvers == [
            "module_manager",
            "r_and_d_director",
            "quality_engineer",
        ]

        # CRITICAL → module_manager, r_and_d_director, quality_engineer
        r4 = ApprovalAdvisor.recommend(90.0, "CRITICAL", use_llm=False)
        assert r4.required_approvers == [
            "module_manager",
            "r_and_d_director",
            "quality_engineer",
        ]

    # ── 序列化测试 ─────────────────────────────────────────────────────

    def test_recommendation_serializable(self) -> None:
        """推荐结果可序列化为 ApprovalRecommendation Schema"""
        result = ApprovalAdvisor.recommend(
            risk_score=45.0,
            risk_level="MEDIUM",
            use_llm=False,
        )
        serialized = result.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["recommendation"] == "FAST_TRACK"
        assert serialized["risk_score"] == 45.0
        assert serialized["risk_level"] == "MEDIUM"
        assert serialized["confidence"] == 1.0
        assert isinstance(serialized["reason"], str)
        assert isinstance(serialized["required_approvers"], list)

    def test_llm_recommend_failure_does_not_crash(self) -> None:
        """_llm_recommend 实现中任何异常不导致崩溃"""
        # 直接调用 _llm_recommend — 不需要 mock，因为会调用 ai_chat
        # 但 ai_chat 会在没有 API key 时失败，这正是我们要验证的优雅降级
        result = ApprovalAdvisor._llm_recommend(
            risk_score=50.0,
            risk_level="MEDIUM",
        )
        # 在没有 API key 的环境下应返回 None（而不是抛出异常）
        assert result is None

    # ── 架构约束验证 ────────────────────────────────────────────────────

    def test_no_ecr_eco_modification(self) -> None:
        """架构约束：ApprovalAdvisor 不修改任何 ECR/ECO 状态

        验证方法：检查推荐结果中不含 status 相关字段，
        ApprovalRecommendation 不含 status 修改语义。
        """
        result = ApprovalAdvisor.recommend(20.0, "LOW", use_llm=False)
        serialized = result.model_dump()
        # 不应包含任何状态相关字段
        assert "status" not in serialized
        assert "ecr" not in str(serialized.get("reason", "")).lower()
        assert "eco" not in str(serialized.get("reason", "")).lower()


class TestApprovalAdvisorHelpers:
    """ApprovalAdvisor 辅助方法单元测试"""

    def test_format_risk_context_no_graph(self) -> None:
        """_format_risk_context: 无 impact_graph"""
        context = ApprovalAdvisor._format_risk_context(
            risk_score=45.0,
            risk_level="MEDIUM",
        )
        assert "风险评分: 45.0" in context
        assert "风险等级: MEDIUM" in context
        assert "AUTO_APPROVE" in context
        assert "变更影响图" not in context

    def test_format_risk_context_with_graph(self) -> None:
        """_format_risk_context: 有 impact_graph"""
        graph = ImpactGraphOut(
            nodes=[
                ImpactNode(
                    id="n1", node_type="bom", label="BOM变更",
                    impact_score=0.5, affected_objects=[{}], depth=1,
                ),
            ],
            edges=[],
            ripple_score=25.0,
            max_depth=1,
            node_count=1,
            edge_count=0,
        )
        context = ApprovalAdvisor._format_risk_context(
            risk_score=85.0,
            risk_level="CRITICAL",
            impact_graph=graph,
        )
        assert "风险评分: 85.0" in context
        assert "CRITICAL" in context
        assert "变更影响图" in context
        assert "节点数: 1" in context
        assert "ripple_score" in context or "Ripple Score" in context

    def test_generate_rule_reason_low(self) -> None:
        """_generate_rule_reason: LOW → 自动审批"""
        reason = ApprovalAdvisor._generate_rule_reason(
            risk_score=15.0,
            risk_level="LOW",
            recommendation=ApprovalAdvisorAction.AUTO_APPROVE,
        )
        assert "低风险" in reason
        assert "自动审批" in reason

    def test_generate_rule_reason_critical(self) -> None:
        """_generate_rule_reason: CRITICAL → 驳回重新设计"""
        reason = ApprovalAdvisor._generate_rule_reason(
            risk_score=90.0,
            risk_level="CRITICAL",
            recommendation=ApprovalAdvisorAction.REJECT_REDESIGN,
        )
        assert "极高风险" in reason
        assert "重新设计" in reason

    def test_generate_rule_reason_with_graph(self) -> None:
        """_generate_rule_reason: 带有 impact_graph"""
        graph = ImpactGraphOut(
            nodes=[], edges=[], ripple_score=50.0,
            max_depth=0, node_count=5, edge_count=3,
        )
        reason = ApprovalAdvisor._generate_rule_reason(
            risk_score=60.0,
            risk_level="HIGH",
            recommendation=ApprovalAdvisorAction.FULL_APPROVAL,
            impact_graph=graph,
        )
        assert "高风险" in reason
        assert "完整审批" in reason
        assert "5 个节点" in reason
        assert "3 条边" in reason

    def test_recommendation_map_all_levels(self) -> None:
        """RECOMMENDATION_MAP 覆盖所有风险等级"""
        assert ApprovalAdvisor.RECOMMENDATION_MAP["LOW"] == ApprovalAdvisorAction.AUTO_APPROVE
        assert ApprovalAdvisor.RECOMMENDATION_MAP["MEDIUM"] == ApprovalAdvisorAction.FAST_TRACK
        assert ApprovalAdvisor.RECOMMENDATION_MAP["HIGH"] == ApprovalAdvisorAction.FULL_APPROVAL
        assert ApprovalAdvisor.RECOMMENDATION_MAP["CRITICAL"] == ApprovalAdvisorAction.REJECT_REDESIGN

    def test_approver_map_all_levels(self) -> None:
        """APPROVER_MAP 覆盖所有风险等级"""
        assert ApprovalAdvisor.APPROVER_MAP["LOW"] == []
        assert ApprovalAdvisor.APPROVER_MAP["MEDIUM"] == ["module_manager"]
        assert ApprovalAdvisor.APPROVER_MAP["HIGH"] == [
            "module_manager", "r_and_d_director", "quality_engineer",
        ]
        assert ApprovalAdvisor.APPROVER_MAP["CRITICAL"] == [
            "module_manager", "r_and_d_director", "quality_engineer",
        ]

    def test_threshold_constants(self) -> None:
        """阈值常量与 M1 RiskEngine 保持一致"""
        assert ApprovalAdvisor.LOW_THRESHOLD == 30
        assert ApprovalAdvisor.MEDIUM_THRESHOLD == 60
        assert ApprovalAdvisor.HIGH_THRESHOLD == 85
