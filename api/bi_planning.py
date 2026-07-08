"""BI分析 — 策划模块（趋势/漏斗/分布）"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_menu
from app.models.product_plan import ProductPlan
from app.models.project import Project, ProjectGate
from app.models.approval import ApprovalRequest, ApprovalRecord
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bi", tags=["BI分析看板"])

@router.get("/planning")
def bi_planning(
    year: Optional[int] = Query(None, description="筛选年份"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> dict:
    """策划维度聚合统计

    返回: 完成率 / 阶段分布柱状图 / 审批时效P50-P90 / 月度趋势
    """
    result = {}

    # ── 1. 基础筛选 ──
    plan_base = db.query(ProductPlan)
    if year:
        plan_base = plan_base.filter(
            func.extract("YEAR", ProductPlan.created_at) == year
        )

    # ── 2. 完成率（approved+released 占总数的比例） ──
    total_plans = plan_base.count()
    completed = plan_base.filter(
        ProductPlan.status.in_([
            ProductPlanStage.APPROVED,
            ProductPlanStage.RELEASED,
        ])
    ).count()
    result["completion_rate"] = {
        "total": total_plans,
        "completed": completed,
        "rate": round(completed / total_plans * 100, 2) if total_plans > 0 else 0,
    }

    # ── 3. 阶段分布柱状图 ──
    stage_rows = (
        plan_base
        .with_entities(
            ProductPlan.status,
            func.count(ProductPlan.id).label("cnt"),
        )
        .group_by(ProductPlan.status)
        .all()
    )
    result["stage_distribution"] = {
        row.status.value if hasattr(row.status, "value") else str(row.status): row.cnt
        for row in stage_rows
    }

    # ── 4. 审批时效 P50 / P90 ──
    # 用 SQL 窗口函数：approval_requests.created_at 到审批记录的 decided_at
    approval_times = (
        db.query(
            func.timestampdiff(
                text("HOUR"),
                ApprovalRequest.created_at,
                func.max(ApprovalRecord.decided_at),
            ).label("duration_hours"),
        )
        .join(ApprovalRecord, ApprovalRecord.request_id == ApprovalRequest.id)
        .group_by(ApprovalRequest.id)
        .having(func.max(ApprovalRecord.decided_at).isnot(None))
        .subquery()
    )

    # 计算 P50 / P90 用 percentile_cont (MySQL 8.0+)
    # 兼容旧版 MySQL：先取出所有值，在 Python 里算分位数
    all_durations = [
        row[0] for row in db.query(approval_times.c.duration_hours).all()
        if row[0] is not None
    ]
    if all_durations:
        all_durations.sort()
        n = len(all_durations)
        def percentile(arr: list[float], p: float) -> float:
            k = (p / 100.0) * (len(arr) - 1)
            f = int(k)
            c = k - f
            if f + 1 < len(arr):
                return arr[f] + (arr[f + 1] - arr[f]) * c
            return arr[-1] if arr else 0
        result["approval_timeliness"] = {
            "p50_hours": round(percentile(all_durations, 50), 1),
            "p90_hours": round(percentile(all_durations, 90), 1),
            "sample_count": n,
        }
    else:
        result["approval_timeliness"] = {"p50_hours": 0, "p90_hours": 0, "sample_count": 0}

    # ── 5. 月度趋势 ──
    month_rows = (
        plan_base
        .with_entities(
            func.date_format(ProductPlan.created_at, "%Y-%m").label("month"),
            func.count(ProductPlan.id).label("cnt"),
        )
        .group_by(text("month"))
        .order_by(text("month"))
        .all()
    )
    result["monthly_trend"] = {row.month: row.cnt for row in month_rows}

    return result

@router.get("/planning/kpi")
def bi_planning_kpi(
    year: Optional[int] = Query(None, description="筛选年份"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> dict:
    """策划 KPI 汇总"""
    plan_base = db.query(ProductPlan)
    if year:
        plan_base = plan_base.filter(
            func.extract("YEAR", ProductPlan.created_at) == year
        )
    total = plan_base.count()
    completed = plan_base.filter(
        ProductPlan.status.in_([ProductPlanStage.APPROVED, ProductPlanStage.RELEASED])
    ).count()
    return {
        "total_plans": total,
        "completed": completed,
        "completion_rate": round(completed / total * 100, 2) if total > 0 else 0,
    }

@router.get("/planning/phase-distribution")
def bi_planning_phase(
    year: Optional[int] = Query(None, description="筛选年份"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> dict:
    """策划阶段分布"""
    plan_base = db.query(ProductPlan)
    if year:
        plan_base = plan_base.filter(
            func.extract("YEAR", ProductPlan.created_at) == year
        )
    rows = (
        plan_base.with_entities(
            ProductPlan.status,
            func.count(ProductPlan.id).label("cnt"),
        )
        .group_by(ProductPlan.status)
        .all()
    )
    return {
        str(row.status.value) if hasattr(row.status, "value") else str(row.status): row.cnt
        for row in rows
    }

@router.get("/planning/approval-timeline")
def bi_planning_approval(
    year: Optional[int] = Query(None, description="筛选年份"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> dict:
    """审批时效统计"""
    approval_times = (
        db.query(
            func.timestampdiff(
                text("HOUR"),
                ApprovalRequest.created_at,
                func.max(ApprovalRecord.decided_at),
            ).label("duration_hours"),
        )
        .join(ApprovalRecord, ApprovalRecord.request_id == ApprovalRequest.id)
        .group_by(ApprovalRequest.id)
    )
    if year:
        approval_times = approval_times.filter(
            func.extract("YEAR", ApprovalRequest.created_at) == year
        )
    hours = [r.duration_hours for r in approval_times.all() if r.duration_hours is not None]
    if not hours:
        return {"p50": 0, "p90": 0, "avg": 0, "samples": 0}
    hours.sort()
    n = len(hours)
    return {
        "p50": hours[int(n * 0.5)],
        "p90": hours[int(n * 0.9)],
        "avg": round(sum(hours) / n, 1),
        "samples": n,
    }
