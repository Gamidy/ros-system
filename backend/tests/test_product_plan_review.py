"""D4-2 自动偏差计算 — 单元测试

覆盖场景：
  - 成本偏差计算正确（_calc_cost_metrics + auto_calculate_variance）
  - 进度偏差计算正确（_calc_schedule_metrics）
  - 无项目数据时显示"等待"
  - 手动覆盖开关正确（_review_to_dict auto/manual 逻辑）
"""
from __future__ import annotations

from datetime import date
from typing import Any, Generator

import pytest
from sqlalchemy.orm import Session

from app.api.product_plan_review import (
    _review_to_dict,
    auto_calculate_variance,
)
from app.models.product_plan import (
    Cost,
    CostType,
    ProductPlan,
    ProductPlanProjectLink,
    ProductPlanReview,
    ProductPlanStage,
)
from app.models.product_plan_subs import ProductPlanInitiation
from app.models.project import Project


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
def _create_plan(
    db: Session,
    plan_id: str,
    name: str = "Test Plan",
    status: ProductPlanStage = ProductPlanStage.DRAFT,
) -> ProductPlan:
    plan = ProductPlan(id=plan_id, name=name, status=status)
    db.add(plan)
    db.commit()
    return plan


def _create_project(db: Session, project_id: int | None = None) -> Project:
    proj = Project(
        id=project_id or 1,
        code="TEST-PRJ",
        name="Test Project",
        project_class="B",
        status="completed",
    )
    db.add(proj)
    db.commit()
    return proj


# ===================================================================
# 测试类
# ===================================================================
class TestAutoCalculateCostVariance:
    """成本偏差计算"""

    def test_auto_calculate_cost_variance(self, db_session: Session) -> None:
        """成本偏差计算正确：目标 10 万，实际 12 万 → +20%"""
        plan = _create_plan(db_session, "plan-cost-variance")

        cost_target = Cost(
            product_plan_id=plan.id,
            cost_type=CostType.TARGET,
            item_name="BOM目标成本",
            target_value=100_000.0,
        )
        cost_actual = Cost(
            product_plan_id=plan.id,
            cost_type=CostType.ACTUAL,
            item_name="BOM实际成本",
            actual_value=120_000.0,
        )
        db_session.add_all([cost_target, cost_actual])
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["cost_variance_pct"] == 20.0  # (120k-100k)/100k*100
        assert result["target_cost_total"] == 100_000.0
        assert result["actual_cost_total"] == 120_000.0
        assert result["has_project_data"] is True

    def test_cost_variance_negative(self, db_session: Session) -> None:
        """成本偏差为负数（实际低于目标）"""
        plan = _create_plan(db_session, "plan-cost-below")

        cost_target = Cost(
            product_plan_id=plan.id,
            cost_type=CostType.TARGET,
            item_name="目标",
            target_value=200_000.0,
        )
        cost_actual = Cost(
            product_plan_id=plan.id,
            cost_type=CostType.ACTUAL,
            item_name="实际",
            actual_value=150_000.0,
        )
        db_session.add_all([cost_target, cost_actual])
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["cost_variance_pct"] == -25.0  # (150k-200k)/200k*100
        assert result["has_project_data"] is True

    def test_cost_variance_zero_actual(self, db_session: Session) -> None:
        """目标存在但实际为 0 时，不计算偏差（actual_cost_total == 0）"""
        plan = _create_plan(db_session, "plan-cost-no-actual")

        cost_target = Cost(
            product_plan_id=plan.id,
            cost_type=CostType.TARGET,
            item_name="目标",
            target_value=100_000.0,
        )
        db_session.add(cost_target)
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["cost_variance_pct"] is None
        assert result["target_cost_total"] == 100_000.0
        assert result["actual_cost_total"] == 0.0
        assert result["has_project_data"] is True  # 有 target 也算有数据


class TestAutoCalculateScheduleVariance:
    """进度偏差计算"""

    def test_auto_calculate_schedule_variance(self, db_session: Session) -> None:
        """进度偏差计算正确：计划 1月1日，实际 4月1日 → +90 天"""
        plan = _create_plan(db_session, "plan-schedule-variance")

        # 计划上市日期
        initiation = ProductPlanInitiation(
            product_plan_id=plan.id,
            required_date=date(2026, 1, 1),
        )
        db_session.add(initiation)
        db_session.commit()

        # 关联项目 + 实际结束日期
        proj = _create_project(db_session, 100)
        proj.actual_end_date = date(2026, 4, 1)
        db_session.flush()

        link = ProductPlanProjectLink(
            product_plan_id=plan.id,
            project_id=proj.id,
            link_type="primary",
        )
        db_session.add(link)
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["schedule_variance_days"] == 90
        assert result["planned_launch_date"] == "2026-01-01"
        assert result["actual_launch_date"] == "2026-04-01"
        assert result["has_project_data"] is True

    def test_schedule_variance_negative(self, db_session: Session) -> None:
        """进度偏差为负数（提前完成）"""
        plan = _create_plan(db_session, "plan-schedule-early")

        initiation = ProductPlanInitiation(
            product_plan_id=plan.id,
            required_date=date(2026, 6, 1),
        )
        db_session.add(initiation)
        db_session.commit()

        proj = _create_project(db_session, 101)
        proj.actual_end_date = date(2026, 3, 1)
        db_session.flush()

        link = ProductPlanProjectLink(
            product_plan_id=plan.id,
            project_id=proj.id,
            link_type="primary",
        )
        db_session.add(link)
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["schedule_variance_days"] == -92  # Mar 1 - Jun 1 = -92 days
        assert result["has_project_data"] is True

    def test_schedule_no_actual_date(self, db_session: Session) -> None:
        """有计划日期但无实际日期时，schedule_variance_days 为 None"""
        plan = _create_plan(db_session, "plan-schedule-no-actual")

        initiation = ProductPlanInitiation(
            product_plan_id=plan.id,
            required_date=date(2026, 1, 1),
        )
        db_session.add(initiation)
        db_session.commit()

        proj = _create_project(db_session, 102)
        # 不设置 actual_end_date
        db_session.flush()

        link = ProductPlanProjectLink(
            product_plan_id=plan.id,
            project_id=proj.id,
            link_type="primary",
        )
        db_session.add(link)
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["schedule_variance_days"] is None
        assert result["planned_launch_date"] == "2026-01-01"
        assert result["actual_launch_date"] is None
        assert result["has_project_data"] is True


class TestNoProjectData:
    """无项目数据场景"""

    def test_no_project_data(self, db_session: Session) -> None:
        """无任何关联数据时 has_project_data=False"""
        plan = _create_plan(db_session, "plan-no-data-at-all")
        # 不添加 Cost/Initiation/ProjectLink

        result = auto_calculate_variance(plan.id, db_session)

        assert result["has_project_data"] is False
        assert result["cost_variance_pct"] is None
        assert result["schedule_variance_days"] is None
        assert result["target_cost_total"] == 0.0
        assert result["actual_cost_total"] == 0.0
        assert result["planned_launch_date"] is None
        assert result["actual_launch_date"] is None

    def test_only_target_cost_no_actual(self, db_session: Session) -> None:
        """只有目标成本没有实际成本 → has_project_data=True 但 cost_variance_pct=None"""
        plan = _create_plan(db_session, "plan-target-only")

        cost_target = Cost(
            product_plan_id=plan.id,
            cost_type=CostType.TARGET,
            item_name="目标",
            target_value=50_000.0,
        )
        db_session.add(cost_target)
        db_session.commit()

        result = auto_calculate_variance(plan.id, db_session)

        assert result["has_project_data"] is True
        assert result["cost_variance_pct"] is None  # actual 为 0，不触发公式
        assert result["target_cost_total"] == 50_000.0
        assert result["actual_cost_total"] == 0.0


class TestManualOverride:
    """手动覆盖开关"""

    def _create_review(
        self,
        db: Session,
        plan_id: str,
        *,
        cost_variance_pct: float | None = None,
        schedule_variance_days: int | None = None,
    ) -> ProductPlanReview:
        review = ProductPlanReview(
            product_plan_id=plan_id,
            cost_variance_pct=cost_variance_pct,
            schedule_variance_days=schedule_variance_days,
        )
        db.add(review)
        db.flush()
        return review

    def test_auto_fills_when_manual_empty(self, db_session: Session) -> None:
        """数据库值为空且有自动计算值时 → 填充 auto，source='auto'"""
        plan = _create_plan(db_session, "plan-override-auto")

        review = self._create_review(db_session, plan.id)

        auto_variance: dict[str, Any] = {
            "cost_variance_pct": 15.5,
            "schedule_variance_days": 30,
        }
        result = _review_to_dict(review, auto_variance)

        assert result["cost_variance_pct"] == 15.5
        assert result["cost_variance_source"] == "auto"
        assert result["cost_variance_pct_auto"] == 15.5
        assert result["schedule_variance_days"] == 30
        assert result["schedule_variance_source"] == "auto"
        assert result["schedule_variance_days_auto"] == 30

    def test_manual_values_override_auto(self, db_session: Session) -> None:
        """数据库有值时 → 使用手动值，source='manual'"""
        plan = _create_plan(db_session, "plan-override-manual")

        review = self._create_review(
            db_session,
            plan.id,
            cost_variance_pct=8.0,
            schedule_variance_days=15,
        )

        auto_variance: dict[str, Any] = {
            "cost_variance_pct": 20.0,
            "schedule_variance_days": 45,
        }
        result = _review_to_dict(review, auto_variance)

        assert result["cost_variance_pct"] == 8.0  # 手动值优先
        assert result["cost_variance_source"] == "manual"
        assert result["schedule_variance_days"] == 15
        assert result["schedule_variance_source"] == "manual"
        # auto_ 字段仍然有原始值
        assert result["cost_variance_pct_auto"] == 20.0
        assert result["schedule_variance_days_auto"] == 45

    def test_no_auto_variance_preserves_manual(self, db_session: Session) -> None:
        """没有 auto_variance 数据时 → 保持原有 manual 值"""
        plan = _create_plan(db_session, "plan-override-no-auto")

        review = self._create_review(
            db_session,
            plan.id,
            cost_variance_pct=5.0,
            schedule_variance_days=10,
        )

        result = _review_to_dict(review, auto_variance=None)

        assert result["cost_variance_pct"] == 5.0
        assert result["cost_variance_source"] == "manual"
        assert result["cost_variance_pct_auto"] is None
        assert result["schedule_variance_days"] == 10
        assert result["schedule_variance_source"] == "manual"
        assert result["schedule_variance_days_auto"] is None

    def test_no_auto_variance_empty_manual(self, db_session: Session) -> None:
        """都没有数据时 → 所有值为 None，source='manual'"""
        plan = _create_plan(db_session, "plan-override-none")

        review = self._create_review(db_session, plan.id)

        result = _review_to_dict(review, auto_variance=None)

        assert result["cost_variance_pct"] is None
        assert result["cost_variance_source"] == "manual"
        assert result["schedule_variance_days"] is None
        assert result["schedule_variance_source"] == "manual"
