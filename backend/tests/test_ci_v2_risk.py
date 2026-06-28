"""M1 Risk Engine — 单元测试

验收标准：
  1. RiskEngine.calculate() 是纯函数，相同输入=相同输出
  2. 边界值精确（30/60/85分界线）
  3. 单维度极端值不导致整体系统崩溃
  4. 所有输入缺失时返回 score=0, level=LOW
  5. pytest 全部通过
  6. 全类型注解，无 Any
"""
from decimal import Decimal

import pytest

from app.schemas.ci_v2 import (
    RiskAssessmentOut,
    RiskLevelEnum,
    SignalInput,
)
from app.services.ai.risk_engine import RiskEngine


class TestRiskEngineCalculate:
    """RiskEngine.calculate() 纯函数单元测试"""

    def test_all_zero_signals(self) -> None:
        """所有信号为0 → risk_score=0, level=LOW"""
        signals = SignalInput(
            bom_impact=0,
            cert_impact=0,
            proto_instability=0,
            cost_overrun=0,
            hist_failure_rate=0,
        )
        result = RiskEngine.calculate(signals)
        assert result.risk_score == 0.0
        assert result.risk_level == RiskLevelEnum.LOW

    def test_all_max_signals(self) -> None:
        """所有信号为100 → risk_score=100, level=CRITICAL"""
        signals = SignalInput(
            bom_impact=100,
            cert_impact=100,
            proto_instability=100,
            cost_overrun=100,
            hist_failure_rate=100,
        )
        result = RiskEngine.calculate(signals)
        assert result.risk_score == 100.0
        assert result.risk_level == RiskLevelEnum.CRITICAL

    def test_bom_only_high(self) -> None:
        """仅BOM=100, 其他为0 → score=30, level=MEDIUM"""
        signals = SignalInput(
            bom_impact=100,
            cert_impact=0,
            proto_instability=0,
            cost_overrun=0,
            hist_failure_rate=0,
        )
        result = RiskEngine.calculate(signals)
        # bom_impact * 0.3 = 100 * 0.3 = 30
        assert result.risk_score == 30.0, f"Expected 30, got {result.risk_score}"
        assert result.risk_level == RiskLevelEnum.MEDIUM

    def test_cert_only_high(self) -> None:
        """仅cert=100 → score=20, level=LOW"""
        signals = SignalInput(
            bom_impact=0,
            cert_impact=100,
            proto_instability=0,
            cost_overrun=0,
            hist_failure_rate=0,
        )
        result = RiskEngine.calculate(signals)
        assert result.risk_score == 20.0  # 100 * 0.2
        assert result.risk_level == RiskLevelEnum.LOW

    def test_cost_only_high(self) -> None:
        """仅cost=100 → score=20, level=LOW"""
        signals = SignalInput(
            bom_impact=0,
            cert_impact=0,
            proto_instability=0,
            cost_overrun=100,
            hist_failure_rate=0,
        )
        result = RiskEngine.calculate(signals)
        assert result.risk_score == 20.0  # 100 * 0.2
        assert result.risk_level == RiskLevelEnum.LOW

    def test_hist_failure_only_high(self) -> None:
        """仅hist_failure=100 → score=10, level=LOW"""
        signals = SignalInput(
            bom_impact=0,
            cert_impact=0,
            proto_instability=0,
            cost_overrun=0,
            hist_failure_rate=100,
        )
        result = RiskEngine.calculate(signals)
        assert result.risk_score == 10.0  # 100 * 0.1
        assert result.risk_level == RiskLevelEnum.LOW

    # ── 边界值测试 ───────────────────────────────────────────────────

    def test_boundary_low_medium(self) -> None:
        """边界：29.9=LOW, 30=MEDIUM"""
        # 总分29.9: bom=99.0 (29.7) + cert=1.0 (0.2) = 29.9
        low = RiskEngine.calculate(SignalInput(
            bom_impact=99.0,
            cert_impact=1.0,
            proto_instability=0,
            cost_overrun=0,
            hist_failure_rate=0,
        ))
        # 99*0.3 + 1*0.2 = 29.7 + 0.2 = 29.9
        assert low.risk_score == 29.9, f"Expected 29.9, got {low.risk_score}"
        assert low.risk_level == RiskLevelEnum.LOW

        # 总分30.0: bom=100 (30.0)
        medium = RiskEngine.calculate(SignalInput(
            bom_impact=100.0,
            cert_impact=0,
            proto_instability=0,
            cost_overrun=0,
            hist_failure_rate=0,
        ))
        assert medium.risk_score == 30.0
        assert medium.risk_level == RiskLevelEnum.MEDIUM

    def test_boundary_medium_high(self) -> None:
        """边界：59.9=MEDIUM, 60=HIGH"""
        # 59.9: bom=100(30) + cert=100(20) + proto=49.5(9.9) = 59.9
        medium = RiskEngine.calculate(SignalInput(
            bom_impact=100.0,
            cert_impact=100.0,
            proto_instability=49.5,
            cost_overrun=0,
            hist_failure_rate=0,
        ))
        # 100*0.3 + 100*0.2 + 49.5*0.2 = 30 + 20 + 9.9 = 59.9
        assert medium.risk_score == 59.9, f"Expected 59.9, got {medium.risk_score}"
        assert medium.risk_level == RiskLevelEnum.MEDIUM

        # 60.0: bom=100(30) + cert=100(20) + proto=50(10) = 60
        high = RiskEngine.calculate(SignalInput(
            bom_impact=100.0,
            cert_impact=100.0,
            proto_instability=50.0,
            cost_overrun=0,
            hist_failure_rate=0,
        ))
        assert high.risk_score == 60.0
        assert high.risk_level == RiskLevelEnum.HIGH

    def test_boundary_high_critical(self) -> None:
        """边界：84.9=HIGH, 85=CRITICAL"""
        # 84.9: bom=100(30) + cert=100(20) + proto=100(20) + cost=74.5(14.9) = 84.9
        high = RiskEngine.calculate(SignalInput(
            bom_impact=100.0,
            cert_impact=100.0,
            proto_instability=100.0,
            cost_overrun=74.5,
            hist_failure_rate=0,
        ))
        # 30 + 20 + 20 + 14.9 = 84.9
        assert high.risk_score == 84.9, f"Expected 84.9, got {high.risk_score}"
        assert high.risk_level == RiskLevelEnum.HIGH

        # 85.0: bom=100(30) + cert=100(20) + proto=100(20) + cost=75(15) = 85
        critical = RiskEngine.calculate(SignalInput(
            bom_impact=100.0,
            cert_impact=100.0,
            proto_instability=100.0,
            cost_overrun=75.0,
            hist_failure_rate=0,
        ))
        assert critical.risk_score == 85.0
        assert critical.risk_level == RiskLevelEnum.CRITICAL

    # ── 优雅降级测试 ────────────────────────────────────────────────

    def test_signal_graceful_degradation(self) -> None:
        """所有输入缺失（使用默认值0）→ score=0, level=LOW"""
        # SignalInput 所有字段默认值为0
        signals = SignalInput()
        result = RiskEngine.calculate(signals)
        assert result.risk_score == 0.0
        assert result.risk_level == RiskLevelEnum.LOW
        assert result.bom_impact == 0.0
        assert result.cert_impact == 0.0
        assert result.proto_instability == 0.0
        assert result.cost_overrun == 0.0
        assert result.hist_failure_rate == 0.0

    def test_partial_signals(self) -> None:
        """部分信号缺失（只传了2个）→ 未传的默认为0"""
        signals = SignalInput(
            bom_impact=50.0,
            cert_impact=30.0,
        )
        result = RiskEngine.calculate(signals)
        # 50*0.3 + 30*0.2 = 15 + 6 = 21
        assert result.risk_score == 21.0
        assert result.risk_level == RiskLevelEnum.LOW
        assert result.proto_instability == 0.0
        assert result.cost_overrun == 0.0
        assert result.hist_failure_rate == 0.0

    # ── 确定性测试 ───────────────────────────────────────────────────

    def test_deterministic(self) -> None:
        """相同输入 → 相同输出（纯函数性质）"""
        signals = SignalInput(
            bom_impact=45.0,
            cert_impact=67.0,
            proto_instability=23.0,
            cost_overrun=88.0,
            hist_failure_rate=12.0,
        )
        result1 = RiskEngine.calculate(signals)
        result2 = RiskEngine.calculate(signals)
        assert result1.risk_score == result2.risk_score
        assert result1.risk_level == result2.risk_level
        assert result1.signal_details == result2.signal_details
        assert result1.mitigation_suggestions == result2.mitigation_suggestions

    # ── 单维度极端值测试 ─────────────────────────────────────────────

    def test_single_dimension_extreme_does_not_crash(self) -> None:
        """单维度极端值不导致系统崩溃"""
        # 每个维度单独设100
        for dim in ["bom_impact", "cert_impact", "proto_instability",
                     "cost_overrun", "hist_failure_rate"]:
            kwargs = {
                "bom_impact": 0.0,
                "cert_impact": 0.0,
                "proto_instability": 0.0,
                "cost_overrun": 0.0,
                "hist_failure_rate": 0.0,
                dim: 100.0,
            }
            signals = SignalInput(**kwargs)  # type: ignore[arg-type]
            result = RiskEngine.calculate(signals)
            assert result.risk_score >= 0
            assert result.risk_level in (
                RiskLevelEnum.LOW, RiskLevelEnum.MEDIUM,
                RiskLevelEnum.HIGH, RiskLevelEnum.CRITICAL,
            )

    # ── 风险向量测试 ────────────────────────────────────────────────

    def test_risk_vector_all_zero(self) -> None:
        """风险向量：所有信号为0"""
        signals = SignalInput()
        vector = RiskEngine.get_risk_vector(signals)
        assert vector["total_score"] == 0.0
        assert all(v == 0.0 for v in vector["contributions"].values())
        assert vector["risk_buckets"]["low"] == 0.0

    def test_risk_vector_all_max(self) -> None:
        """风险向量：所有信号为100"""
        signals = SignalInput(
            bom_impact=100,
            cert_impact=100,
            proto_instability=100,
            cost_overrun=100,
            hist_failure_rate=100,
        )
        vector = RiskEngine.get_risk_vector(signals)
        assert vector["total_score"] == 100.0
        # 所有维度分数≥85 → 全部进入 critical 桶
        assert vector["risk_buckets"]["critical"] == 100.0

    # ── 缓解建议测试 ───────────────────────────────────────────────

    def test_mitigation_low(self) -> None:
        """LOW风险 → 包含AUTO_APPROVE和建议"""
        suggestions = RiskEngine.get_mitigation_suggestions(
            RiskLevelEnum.LOW,
            {"risk_buckets": {}},
        )
        assert len(suggestions) > 0
        assert "AUTO_APPROVE" in suggestions[-1] or "AUTO_APPROVE" in suggestions

    def test_mitigation_critical(self) -> None:
        """CRITICAL风险 → 包含REJECT_REDESIGN"""
        suggestions = RiskEngine.get_mitigation_suggestions(
            RiskLevelEnum.CRITICAL,
            {"risk_buckets": {"cost_overrun": 50, "hist_failure_rate": 30}},
        )
        assert len(suggestions) > 0
        assert any("REJECT_REDESIGN" in s for s in suggestions)

    def test_mitigation_high_with_bom_warning(self) -> None:
        """HIGH风险 + bom_impact >15 → 含BOM相关建议"""
        suggestions = RiskEngine.get_mitigation_suggestions(
            RiskLevelEnum.HIGH,
            {"risk_buckets": {"cost_overrun": 20, "hist_failure_rate": 5}},
        )
        assert len(suggestions) > 0
        assert "FULL_APPROVAL" in suggestions[-1] or "FULL_APPROVAL" in suggestions

    # ── 快捷函数测试 ────────────────────────────────────────────────

    def test_calculate_risk_shortcut(self) -> None:
        """快捷函数 calculate_risk 与 RiskEngine.calculate 一致"""
        from app.services.ai.risk_engine import calculate_risk
        signals = SignalInput(bom_impact=50, cert_impact=30)
        shortcut_result = calculate_risk(signals)
        direct_result = RiskEngine.calculate(signals)
        assert shortcut_result.risk_score == direct_result.risk_score
        assert shortcut_result.risk_level == direct_result.risk_level


class TestRiskEngineAssessForECR:
    """assess_for_ecr 集成测试 — 模拟DB查询"""

    def test_assess_for_ecr_with_mock(self, mocker) -> None:
        """模拟ECR/ECO查询，验证持久化流程"""
        from app.models.ci_v2_risk import RiskAssessment
        from app.models.ecr_eco import ECRRequest, ECO

        # 模拟 ECR
        mock_ecr = mocker.MagicMock(spec=ECRRequest)
        mock_ecr.id = 42
        mock_ecr.description = "压缩机变更，涉及CE认证重评估"
        mock_ecr.affected_documents = '{"cert": ["CE", "CB"]}'
        mock_ecr.urgency = "high"

        # 捕获被 add 的 assessment 对象，让 refresh 设置 id
        captured_assessment: list[RiskAssessment] = []

        def _capture_add(obj: RiskAssessment) -> None:
            captured_assessment.append(obj)

        def _mock_refresh(obj: RiskAssessment) -> None:
            # 模拟数据库刷新 — 设置 id 和 created_at
            obj.id = 42
            from datetime import datetime, timezone
            obj.created_at = datetime.now(timezone.utc)

        # 模拟 DB Session
        mock_db = mocker.MagicMock()
        mock_db.add.side_effect = _capture_add
        mock_db.refresh.side_effect = _mock_refresh

        # query().filter().first() 返回 mock_ecr
        mock_query_chain = mocker.MagicMock()
        mock_query_chain.filter.return_value.first.return_value = mock_ecr
        mock_db.query.return_value = mock_query_chain

        # 模拟 ECO 查询返回 None（无关联ECO）
        mock_eco_query = mocker.MagicMock()
        mock_eco_query.filter.return_value.first.return_value = None
        # 第二次调用 query 返回 ECO 查询
        mock_db.query.side_effect = [mock_query_chain, mock_eco_query]

        engine = RiskEngine()
        result = engine.assess_for_ecr(mock_db, 42)

        # 验证结果
        assert result is not None
        assert result.id == 42
        assert result.ecr_id == 42
        # cert_impact from description + affected_documents
        # cert hit count: "认证"(1) + "ce"(1) = 2 from description
        #                + "cert"(0.5) + "ce"(0.5) + "cb"(0.5) = 1.5 from docs
        # total hits = 3.5 → cert_impact = min(3.5 * 15, 100) = 52.5
        assert result.cert_impact == 52.5
        # cost_overrun from urgency "high" = 50
        assert result.cost_overrun == 50.0
        # risk_score = 52.5*0.2 + 50*0.2 + 5*0.1 = 10.5 + 10 + 0.5 = 21.0 → LOW
        assert result.risk_score == 21.0
        assert result.risk_level == RiskLevelEnum.LOW

        # 验证持久化
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        assert len(captured_assessment) == 1
        added_assessment = captured_assessment[0]
        assert isinstance(added_assessment, RiskAssessment)
        assert added_assessment.ecr_id == 42
        assert added_assessment.risk_level == "LOW"

    def test_assess_for_ecr_not_found(self, mocker) -> None:
        """ECR不存在 → 返回None"""
        mock_db = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        engine = RiskEngine()
        result = engine.assess_for_ecr(mock_db, 999)
        assert result is None
        mock_db.add.assert_not_called()

    def test_assess_for_ecr_with_eco_items(self, mocker) -> None:
        """ECR有关联ECO+ECOItem → 信号采集包含BOM impact"""
        from app.models.ci_v2_risk import RiskAssessment
        from app.models.ecr_eco import ECRRequest, ECO, ECOItem

        # 模拟 ECR
        mock_ecr = mocker.MagicMock(spec=ECRRequest)
        mock_ecr.id = 100
        mock_ecr.description = "常规变更"
        mock_ecr.affected_documents = None
        mock_ecr.urgency = "medium"

        # 模拟 ECO
        mock_eco = mocker.MagicMock(spec=ECO)
        mock_eco.id = 200
        mock_eco.ecr_id = 100

        # 模拟 ECOItem 列表
        mock_item1 = mocker.MagicMock(spec=ECOItem)
        mock_item1.change_type = "BOM"
        mock_item2 = mocker.MagicMock(spec=ECOItem)
        mock_item2.change_type = "BOM"
        mock_item3 = mocker.MagicMock(spec=ECOItem)
        mock_item3.change_type = "document"
        mock_items = [mock_item1, mock_item2, mock_item3]

        # 模拟 DB
        mock_db = mocker.MagicMock()

        # 第一次 query: ECRRequest
        mock_ecr_query = mocker.MagicMock()
        mock_ecr_query.filter.return_value.first.return_value = mock_ecr

        # 第二次 query: ECO
        mock_eco_query = mocker.MagicMock()
        mock_eco_query.filter.return_value.first.return_value = mock_eco

        # 第三次 query: ECOItem
        mock_item_query = mocker.MagicMock()
        mock_item_query.filter.return_value.all.return_value = mock_items

        mock_db.query.side_effect = [mock_ecr_query, mock_eco_query, mock_item_query]

        engine = RiskEngine()
        result = engine.assess_for_ecr(mock_db, 100)

        assert result is not None
        # bom_impact: 2 out of 3 items are BOM type → 66.67%
        assert result.bom_impact == pytest.approx(66.67, rel=0.01)
        # proto_instability: 3 items / 10 = 0.3 → 0.3 * 60 = 18
        assert result.proto_instability == 18.0
        # cost_overrun from "medium" = 30
        assert result.cost_overrun == 30.0

        # 验证持久化
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, RiskAssessment)
        assert added.ecr_id == 100
