"""预警引擎逻辑 — 扫描策划表检测逾期/滞留/成本超标"""
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.cost_accounting import CostAccountingSheet, SheetStatus
from app.schemas.dashboard import AlertItem, AlertsSummaryResponse

# ── 预警阈值 ──
TERMINAL_STAGES = {ProductPlanStage.APPROVED, ProductPlanStage.RELEASED}
OVERDUE_DAYS = 30  # 逾期阈值：超过30天未完成
STUCK_DAYS = 7  # 滞留阈值：同一阶段停留超过7天
COST_OVERRUN_RATIO = 1.1  # 成本超标阈值：实际 > 目标 * 1.1


def get_active_plans_with_sheet_map(db: Session) -> tuple[list, dict[str, tuple[float, float]]]:
    """获取全部未终态策划及对应的成本核算表映射

    Returns:
        (active_plans, sheet_map) — sheet_map: plan_id -> (total_cost_actual, total_cost_target)
    """
    now = datetime.now(timezone.utc)
    active_plans = (
        db.query(
            ProductPlan.id,
            ProductPlan.name,
            ProductPlan.status,
            ProductPlan.created_at,
            ProductPlan.updated_at,
        )
        .filter(~ProductPlan.status.in_(TERMINAL_STAGES))
        .all()
    )
    plan_ids = [r.id for r in active_plans]
    sheet_map: dict[str, tuple[float, float]] = {}
    if plan_ids:
        sheet_rows = (
            db.query(
                CostAccountingSheet.product_plan_id,
                CostAccountingSheet.total_cost_actual,
                CostAccountingSheet.total_cost_target,
            )
            .filter(
                CostAccountingSheet.product_plan_id.in_(plan_ids),
                CostAccountingSheet.status == SheetStatus.FINALIZED,
            )
            .all()
        )
        for r in sheet_rows:
            if r.product_plan_id not in sheet_map:
                sheet_map[r.product_plan_id] = (
                    r.total_cost_actual or 0,
                    r.total_cost_target or 0,
                )
    return active_plans, sheet_map


def detect_overdue_alerts(
    active_plans: list,
    today: date,
    now: datetime,
    _existing: list[AlertItem],
) -> list[AlertItem]:
    """检测逾期预警 — 创建超过 OVERDUE_DAYS 天且未完成

    Args:
        active_plans: 未终态策划列表
        today: 当前日期
        now: 当前时间
        existing: 已有预警列表（避免重复）

    Returns:
        新增逾期预警列表
    """
    result: list[AlertItem] = []
    for row in active_plans:
        plan_id: str = row.id
        plan_name: str = row.name
        status_val: str = row.status.value if hasattr(row.status, "value") else str(row.status)
        created_at: datetime = row.created_at or now
        days_since_created = (today - created_at.date()).days
        if days_since_created >= OVERDUE_DAYS:
            result.append(
                AlertItem(
                    type="overdue",
                    plan_id=plan_id,
                    plan_name=plan_name,
                    message=f"策划创建 {days_since_created} 天仍在「{status_val}」阶段，请尽快推进",
                    severity=3,
                    status=status_val,
                    created_at=created_at,
                )
            )
    return result


def detect_stuck_alerts(
    active_plans: list,
    today: date,
    now: datetime,
    existing: list[AlertItem],
) -> list[AlertItem]:
    """检测滞留预警 — 同一阶段停留超过 STUCK_DAYS 天

    Args:
        active_plans: 未终态策划列表
        today: 当前日期
        now: 当前时间
        existing: 已有预警列表（用于排重）

    Returns:
        新增滞留预警列表
    """
    existing_overdue_ids = {a.plan_id for a in existing if a.type == "overdue"}
    result: list[AlertItem] = []
    for row in active_plans:
        plan_id: str = row.id
        plan_name: str = row.name
        status_val: str = row.status.value if hasattr(row.status, "value") else str(row.status)
        created_at: datetime = row.created_at or now
        updated_at: datetime = row.updated_at or created_at
        days_since_updated = (today - updated_at.date()).days
        if days_since_updated >= STUCK_DAYS and plan_id not in existing_overdue_ids:
            result.append(
                AlertItem(
                    type="stuck",
                    plan_id=plan_id,
                    plan_name=plan_name,
                    message=f"在「{status_val}」阶段停留 {days_since_updated} 天，请关注推动",
                    severity=1,
                    status=status_val,
                    created_at=created_at,
                )
            )
    return result


def detect_cost_overrun_alerts(db: Session) -> list[AlertItem]:
    """检测成本超标预警 — 实际 > 目标 * COST_OVERRUN_RATIO

    Args:
        db: 数据库会话

    Returns:
        成本超标预警列表
    """
    result: list[AlertItem] = []
    cost_overrun_rows = (
        db.query(
            CostAccountingSheet.product_plan_id,
            CostAccountingSheet.total_cost_actual,
            CostAccountingSheet.total_cost_target,
            CostAccountingSheet.variance_pct,
            ProductPlan.name,
            ProductPlan.status,
            ProductPlan.created_at,
        )
        .join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id)
        .filter(
            CostAccountingSheet.status == SheetStatus.FINALIZED,
            CostAccountingSheet.total_cost_target > 0,
            CostAccountingSheet.total_cost_actual
            > CostAccountingSheet.total_cost_target * COST_OVERRUN_RATIO,
        )
        .all()
    )
    for row in cost_overrun_rows:
        plan_id: str = row.product_plan_id
        plan_name: str = row.name or "(未命名)"
        actual = row.total_cost_actual or 0
        target = row.total_cost_target or 0
        variance_pct = row.variance_pct or 0
        status_val: str = row.status.value if hasattr(row.status, "value") else str(row.status)
        result.append(
            AlertItem(
                type="cost_overrun",
                plan_id=plan_id,
                plan_name=plan_name,
                message=f"成本超支 {variance_pct:.1f}%（实际 ¥{actual:,.0f} / 目标 ¥{target:,.0f}）",
                severity=2,
                status=status_val,
                created_at=row.created_at,
            )
        )
    return result


def deduplicate_and_sort_alerts(alerts: list[AlertItem]) -> list[AlertItem]:
    """去重（plan_id + type）并按严重度+名称排序

    Args:
        alerts: 原始预警列表

    Returns:
        去重排序后的预警列表
    """
    seen: set[tuple[str, str]] = set()
    deduped: list[AlertItem] = []
    for a in alerts:
        key = (a.plan_id, a.type)
        if key not in seen:
            seen.add(key)
            deduped.append(a)
    deduped.sort(key=lambda a: (-a.severity, a.plan_name or ""))
    return deduped


def count_alerts_by_type(alerts: list[AlertItem]) -> tuple[int, int, int]:
    """按类型统计预警数量

    Returns:
        (overdue_count, stuck_count, cost_overrun_count)
    """
    overdue_count = sum(1 for a in alerts if a.type == "overdue")
    stuck_count = sum(1 for a in alerts if a.type == "stuck")
    cost_overrun_count = sum(1 for a in alerts if a.type == "cost_overrun")
    return overdue_count, stuck_count, cost_overrun_count


def build_alerts_summary_response(db: Session) -> AlertsSummaryResponse:
    """构建预警摘要响应 — 主编排函数

    Args:
        db: 数据库会话

    Returns:
        AlertsSummaryResponse 包含预警统计及明细
    """
    now = datetime.now(timezone.utc)
    today = now.date()

    # Step 1: 获取未终态策划及成本表映射
    active_plans, _sheet_map = get_active_plans_with_sheet_map(db)

    # Step 2: 检测各类型预警
    alerts: list[AlertItem] = []
    alerts.extend(detect_overdue_alerts(active_plans, today, now, alerts))
    alerts.extend(detect_stuck_alerts(active_plans, today, now, alerts))
    alerts.extend(detect_cost_overrun_alerts(db))

    # Step 3: 去重 + 排序
    deduped = deduplicate_and_sort_alerts(alerts)

    # Step 4: 统计
    overdue_count, stuck_count, cost_overrun_count = count_alerts_by_type(deduped)

    return AlertsSummaryResponse(
        overdue_count=overdue_count,
        stuck_count=stuck_count,
        cost_overrun_count=cost_overrun_count,
        alerts=deduped,
    )
