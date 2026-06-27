"""D3-3 预警引擎（dashboard.py get_alerts_summary）— 集成测试

覆盖场景：
  - test_overdue_detection      逾期 30 天检测
  - test_stuck_detection        滞留 7 天检测
  - test_cost_overrun_detection 成本超 10% 检测

测试策略：通过 TestClient 调用 /api/dashboard/alerts-summary，
使用 monkeypatch 或直接写入数据库构造测试数据。
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.cost_accounting import (
    CostAccountingPeriod,
    CostAccountingSheet,
    PeriodStatus,
    SheetStatus,
)


# ===================================================================
# Fixture
# ===================================================================
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """提供可写入的数据库会话（表已由 conftest.py setup_db 创建）"""
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ===================================================================
# 辅助函数
# ===================================================================
def _make_plan(
    db: Session,
    plan_id: str,
    *,
    name: str = "Test",
    status: ProductPlanStage = ProductPlanStage.DRAFT,
    created_days_ago: int = 0,
    updated_days_ago: int = 0,
) -> ProductPlan:
    """创建带特定时间戳的 ProductPlan"""
    now = datetime.now(timezone.utc)
    plan = ProductPlan(
        id=plan_id,
        name=name,
        status=status,
        created_at=now - timedelta(days=created_days_ago),
        updated_at=now - timedelta(days=updated_days_ago),
    )
    db.add(plan)
    db.commit()
    return plan


def _make_period(db: Session, period_id: int = 1) -> CostAccountingPeriod:
    period = CostAccountingPeriod(
        id=period_id,
        period_name="2026-Q1",
        start_date="2026-01-01",
        end_date="2026-03-31",
        status=PeriodStatus.ACTIVE,
    )
    db.add(period)
    db.commit()
    return period


def _make_sheet(
    db: Session,
    *,
    plan_id: str,
    period_id: int = 1,
    total_cost_actual: float = 0.0,
    total_cost_target: float = 0.0,
    variance_pct: float = 0.0,
    status: SheetStatus = SheetStatus.FINALIZED,
) -> CostAccountingSheet:
    sheet = CostAccountingSheet(
        sheet_no=f"CAS-{plan_id}",
        product_plan_id=plan_id,
        period_id=period_id,
        status=status,
        total_cost_actual=total_cost_actual,
        total_cost_target=total_cost_target,
        variance_pct=variance_pct,
    )
    db.add(sheet)
    db.commit()
    return sheet


# ===================================================================
# 测试类
# ===================================================================
class TestOverdueDetection:
    """逾期 30 天检测"""

    def test_overdue_created_35_days_ago(self, client: TestClient,
                                          admin_headers: dict[str, str],
                                          db_session: Session) -> None:
        """创建超过 30 天 → 产生 overdue 预警"""
        _make_plan(db_session, "ov-1", name="逾期策划",
                   created_days_ago=35, updated_days_ago=2)

        # 一个正常的策划，不应触发
        _make_plan(db_session, "ok-1", name="正常策划",
                   created_days_ago=5, updated_days_ago=1)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["overdue_count"] >= 1
        overdue = [a for a in data["alerts"] if a["type"] == "overdue"]
        assert any(a["plan_id"] == "ov-1" for a in overdue)
        assert not any(a["plan_id"] == "ok-1" for a in overdue)

    def test_overdue_exact_30_days(self, client: TestClient,
                                   admin_headers: dict[str, str],
                                   db_session: Session) -> None:
        """正好 30 天 → 触发逾期"""
        _make_plan(db_session, "ov-exact", name="正好30天",
                   created_days_ago=30, updated_days_ago=10)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        overdue = [a for a in data["alerts"] if a["type"] == "overdue"]
        assert any(a["plan_id"] == "ov-exact" for a in overdue)

    def test_terminal_plan_no_overdue(self, client: TestClient,
                                      admin_headers: dict[str, str],
                                      db_session: Session) -> None:
        """已终态的策划（APPROVED/RELEASED）即使超期也不触发"""
        _make_plan(db_session, "term-1", name="已终态逾期",
                   status=ProductPlanStage.APPROVED,
                   created_days_ago=60, updated_days_ago=1)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        overdue = [a for a in data["alerts"] if a["type"] == "overdue"]
        assert not any(a["plan_id"] == "term-1" for a in overdue)


class TestStuckDetection:
    """滞留 7 天检测"""

    def test_stuck_10_days(self, client: TestClient,
                           admin_headers: dict[str, str],
                           db_session: Session) -> None:
        """同一阶段停留超过 7 天 → 产生 stuck 预警"""
        _make_plan(db_session, "st-1", name="滞留策划",
                   created_days_ago=20, updated_days_ago=10)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        stuck = [a for a in data["alerts"] if a["type"] == "stuck"]
        assert any(a["plan_id"] == "st-1" for a in stuck)

    def test_stuck_exact_7_days(self, client: TestClient,
                                admin_headers: dict[str, str],
                                db_session: Session) -> None:
        """正好 7 天 → 触发滞留"""
        _make_plan(db_session, "st-exact", name="正好7天",
                   created_days_ago=15, updated_days_ago=7)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        stuck = [a for a in data["alerts"] if a["type"] == "stuck"]
        assert any(a["plan_id"] == "st-exact" for a in stuck)

    def test_stuck_less_than_7_days(self, client: TestClient,
                                    admin_headers: dict[str, str],
                                    db_session: Session) -> None:
        """少于 7 天 → 不触发滞留"""
        _make_plan(db_session, "st-fresh", name="刚更新",
                   created_days_ago=5, updated_days_ago=2)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        stuck = [a for a in data["alerts"] if a["type"] == "stuck"]
        assert not any(a["plan_id"] == "st-fresh" for a in stuck)

    def test_stuck_already_overdue_only_one_alert(self, client: TestClient,
                                                  admin_headers: dict[str, str],
                                                  db_session: Session) -> None:
        """同时满足逾期和滞留 → 只产生 overdue，不重复 stuck"""
        _make_plan(db_session, "both-1", name="逾期又滞留",
                   created_days_ago=40, updated_days_ago=15)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        alerts_for_plan = [a for a in data["alerts"] if a["plan_id"] == "both-1"]
        types = {a["type"] for a in alerts_for_plan}
        assert "overdue" in types
        assert "stuck" not in types  # 滞留被逾期覆盖


class TestCostOverrunDetection:
    """成本超 10% 检测"""

    def test_cost_overrun_actual_gt_110pct(self, client: TestClient,
                                           admin_headers: dict[str, str],
                                           db_session: Session) -> None:
        """实际成本 > 目标 * 1.1 → 产生 cost_overrun 预警"""
        _make_plan(db_session, "co-1", name="超支策划",
                   created_days_ago=5, updated_days_ago=1)
        _make_period(db_session, period_id=100)

        _make_sheet(db_session, plan_id="co-1", period_id=100,
                    total_cost_actual=120_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=20.0)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["cost_overrun_count"] >= 1
        overruns = [a for a in data["alerts"] if a["type"] == "cost_overrun"]
        assert any(a["plan_id"] == "co-1" for a in overruns)

    def test_cost_within_budget_no_alert(self, client: TestClient,
                                         admin_headers: dict[str, str],
                                         db_session: Session) -> None:
        """实际 ≤ 目标 * 1.1 → 不触发超支"""
        _make_plan(db_session, "co-ok", name="预算内",
                   created_days_ago=5, updated_days_ago=1)
        _make_period(db_session, period_id=200)

        _make_sheet(db_session, plan_id="co-ok", period_id=200,
                    total_cost_actual=100_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=0.0)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        # 如果测试数据少，这条不会出现在 cost_overrun 中
        overruns = [a for a in data["alerts"] if a["type"] == "cost_overrun"]
        assert not any(a["plan_id"] == "co-ok" for a in overruns)

    def test_draft_sheet_no_alert(self, client: TestClient,
                                  admin_headers: dict[str, str],
                                  db_session: Session) -> None:
        """未终态的核算单（DRAFT）不触发超支"""
        _make_plan(db_session, "co-draft", name="草稿核算单",
                   created_days_ago=10, updated_days_ago=3)
        _make_period(db_session, period_id=300)

        _make_sheet(db_session, plan_id="co-draft", period_id=300,
                    total_cost_actual=200_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=100.0,
                    status=SheetStatus.DRAFT)  # 未终态

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        overruns = [a for a in data["alerts"] if a["type"] == "cost_overrun"]
        assert not any(a["plan_id"] == "co-draft" for a in overruns)

    def test_mixed_sheets_correct_filter(self, client: TestClient,
                                         admin_headers: dict[str, str],
                                         db_session: Session) -> None:
        """多条数据中只挑选超标已终态的"""
        _make_plan(db_session, "co-mix-1", name="超支1",
                   created_days_ago=10, updated_days_ago=2)
        _make_plan(db_session, "co-mix-2", name="未超支",
                   created_days_ago=8, updated_days_ago=1)
        _make_plan(db_session, "co-mix-3", name="草稿超支",
                   created_days_ago=6, updated_days_ago=1)

        period = _make_period(db_session, period_id=400)

        # 超支且终态 → 应触发
        _make_sheet(db_session, plan_id="co-mix-1", period_id=400,
                    total_cost_actual=150_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=50.0)

        # 未超支 → 不触发
        _make_sheet(db_session, plan_id="co-mix-2", period_id=400,
                    total_cost_actual=90_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=-10.0)

        # 超支但草稿 → 不触发
        _make_sheet(db_session, plan_id="co-mix-3", period_id=400,
                    total_cost_actual=200_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=100.0,
                    status=SheetStatus.DRAFT)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        overruns = [a for a in data["alerts"] if a["type"] == "cost_overrun"]
        overrun_ids = {a["plan_id"] for a in overruns}
        assert "co-mix-1" in overrun_ids
        assert "co-mix-2" not in overrun_ids
        assert "co-mix-3" not in overrun_ids


# ===================================================================
# 组合场景 — 确认全部三种类型同时出现时计数正确
# ===================================================================
class TestCombinedAlerts:
    """三种预警同时出现"""

    def test_all_three_types(self, client: TestClient,
                             admin_headers: dict[str, str],
                             db_session: Session) -> None:
        """同时存在逾期、滞留、超支 → 各自计数 > 0"""

        # 逾期
        _make_plan(db_session, "comb-ov", name="组合逾期",
                   created_days_ago=35, updated_days_ago=10)

        # 滞留（不逾期）
        _make_plan(db_session, "comb-st", name="组合滞留",
                   created_days_ago=14, updated_days_ago=8)

        # 超支
        _make_plan(db_session, "comb-co", name="组合超支",
                   created_days_ago=5, updated_days_ago=1)
        _make_period(db_session, period_id=500)
        _make_sheet(db_session, plan_id="comb-co", period_id=500,
                    total_cost_actual=130_000.0,
                    total_cost_target=100_000.0,
                    variance_pct=30.0)

        resp = client.get("/api/dashboard/alerts-summary", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["overdue_count"] >= 1
        assert data["stuck_count"] >= 1
        assert data["cost_overrun_count"] >= 1
        assert len(data["alerts"]) >= 3
