"""BI分析看板 — 数据聚合API（成本分析已拆分到 bi_cost_analytics.py）"""
from typing import Optional
import json
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_menu
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.project import Project, ProjectGate
from app.models.approval import ApprovalRequest, ApprovalRecord
from app.schemas.bi import TrendItem, TrendResponse, FunnelItem, FunnelResponse, DistributionItem, DistributionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bi", tags=["BI分析看板"])


# ── Redis缓存辅助（降级安全） ──

_redis_pool: Optional['redis.ConnectionPool'] = None


def _redis_client() -> Optional['redis.Redis']:
    """尝试获取 Redis 连接，失败返回 None 避免影响主流程"""
    global _redis_pool
    try:
        import redis as _redis
        if _redis_pool is None:
            _redis_pool = _redis.ConnectionPool(
                host="127.0.0.1", port=6379, socket_connect_timeout=1, decode_responses=True
            )
        return _redis.Redis(connection_pool=_redis_pool)
    except Exception:
        logger.exception(f"unexpected: {e}")
        return None


def _cache_get(key: str) -> Optional[str]:
    """从 Redis 读取缓存，Redis 不可用时返回 None"""
    try:
        r = _redis_client()
        if r is None:
            return None
        val: Optional[str] = r.get(key)
        return val
    except Exception:
        logger.exception(f"unexpected: {e}")
        return None


def _cache_set(key: str, value: str, ttl: int = 600) -> None:
    """写入 Redis 缓存，失败静默忽略"""
    try:
        r = _redis_client()
        if r is None:
            return
        r.setex(key, ttl, value)
    except Exception:
        logger.debug(f"ignored: {{e}}")
        pass


CACHE_TTL = 600  # 10分钟


# ═══════════════════════════════════════════
# 策划维度统计
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# 项目维度统计
# ═══════════════════════════════════════════

@router.get("/projects")
def bi_projects(
    year: Optional[int] = Query(None, description="筛选年份"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> dict:
    """项目维度聚合统计

    返回: M1-M9 Gate通关率 / 阶段停留时长
    """
    # ── 1. Gate 通关率 M1~M9 ──
    gate_base = db.query(ProjectGate)
    if year:
        gate_base = gate_base.filter(
            func.extract("YEAR", ProjectGate.created_at) == year
        )

    gate_rows = (
        gate_base
        .with_entities(
            ProjectGate.gate_code,
            func.count(ProjectGate.id).label("total"),
            func.sum(
                case(
                    (ProjectGate.status == "passed", 1),
                    else_=0,
                )
            ).label("passed"),
            func.sum(
                case(
                    (ProjectGate.status == "failed", 1),
                    else_=0,
                )
            ).label("failed"),
        )
        .group_by(ProjectGate.gate_code)
        .order_by(ProjectGate.gate_code)
        .all()
    )

    project_base = db.query(Project).filter(Project.is_deleted == False)
    if year:
        project_base = project_base.filter(
            func.extract("YEAR", Project.created_at) == year
        )

    result = {
        "gate_pass_rate": [
            {
                "gate": row.gate_code,
                "total": row.total,
                "passed": int(row.passed),
                "failed": int(row.failed),
                "pass_rate": round(
                    int(row.passed) / row.total * 100, 1
                ) if row.total > 0 else 0,
            }
            for row in gate_rows
        ],
    }

    # ── 2. 阶段停留时长 ──
    # 每个 Gate 的 planned_date → actual_date 差值
    stay_rows = (
        gate_base
        .with_entities(
            ProjectGate.gate_code,
            func.avg(
                func.datediff(ProjectGate.actual_date, ProjectGate.planned_date)
            ).label("avg_stay_days"),
            func.min(
                func.datediff(ProjectGate.actual_date, ProjectGate.planned_date)
            ).label("min_stay_days"),
            func.max(
                func.datediff(ProjectGate.actual_date, ProjectGate.planned_date)
            ).label("max_stay_days"),
        )
        .filter(
            ProjectGate.actual_date.isnot(None),
            ProjectGate.planned_date.isnot(None),
        )
        .group_by(ProjectGate.gate_code)
        .order_by(ProjectGate.gate_code)
        .all()
    )

    result["stage_stay_duration"] = [
        {
            "gate": row.gate_code,
            "avg_days": round(float(row.avg_stay_days), 1) if row.avg_stay_days else 0,
            "min_days": row.min_stay_days or 0,
            "max_days": row.max_stay_days or 0,
        }
        for row in stay_rows
    ]

    # ── 3. 项目概况 ──
    status_rows = (
        project_base
        .with_entities(
            Project.status,
            func.count(Project.id).label("cnt"),
        )
        .group_by(Project.status)
        .all()
    )
    result["project_summary"] = {
        row.status: row.cnt for row in status_rows
    }

    class_rows = (
        project_base
        .with_entities(
            Project.project_class,
            func.count(Project.id).label("cnt"),
        )
        .group_by(Project.project_class)
        .all()
    )
    result["project_class_distribution"] = {
        row.project_class: row.cnt for row in class_rows
    }

    return result


# ═══════════════════════════════════════════
# 成本分析已拆分到 bi_cost_analytics.py
# ═══════════════════════════════════════════


# ═══════════════════════════════════════════
# D3-1: 仪表盘多维图表
# ═══════════════════════════════════════════


@router.get("/trend", response_model=TrendResponse)
def bi_trend(
    start_month: Optional[str] = Query(None, description="起始月份 YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月份 YYYY-MM"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> TrendResponse:
    """立项趋势 — 按月份统计产品策划立项数"""
    cache_key = f"bi:trend:{start_month or ''}:{end_month or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return TrendResponse.model_validate_json(cached)

    query = (
        db.query(
            func.date_format(ProductPlan.created_at, "%Y-%m").label("month"),
            func.count(ProductPlan.id).label("count"),
        )
        .group_by(text("month"))
        .order_by(text("month"))
    )
    if start_month:
        query = query.where(func.date_format(ProductPlan.created_at, "%Y-%m") >= start_month)
    if end_month:
        query = query.where(func.date_format(ProductPlan.created_at, "%Y-%m") <= end_month)

    rows = query.all()
    items = [TrendItem(month=row.month, count=row.count) for row in rows]
    result = TrendResponse(items=items)
    _cache_set(cache_key, result.model_dump_json(), CACHE_TTL)
    return result


@router.get("/funnel", response_model=FunnelResponse)
def bi_funnel(
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> FunnelResponse:
    """转化漏斗 — 各阶段策划数量统计"""
    cache_key = "bi:funnel"
    cached = _cache_get(cache_key)
    if cached is not None:
        return FunnelResponse.model_validate_json(cached)

    rows = (
        db.query(
            ProductPlan.status,
            func.count(ProductPlan.id).label("count"),
        )
        .group_by(ProductPlan.status)
        .order_by(func.count(ProductPlan.id).desc())
        .all()
    )

    items = [FunnelItem(name=row.status.value if hasattr(row.status, 'value') else str(row.status), value=row.count) for row in rows]
    result = FunnelResponse(items=items)
    _cache_set(cache_key, result.model_dump_json(), CACHE_TTL)
    return result


@router.get("/distribution", response_model=DistributionResponse)
def bi_distribution(
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> DistributionResponse:
    """市场分布 — 按市场统计策划数量"""
    cache_key = "bi:distribution"
    cached = _cache_get(cache_key)
    if cached is not None:
        return DistributionResponse.model_validate_json(cached)

    rows = (
        db.query(
            func.coalesce(ProductPlan.market, "未指定").label("market"),
            func.count(ProductPlan.id).label("count"),
        )
        .group_by(ProductPlan.market)
        .order_by(func.count(ProductPlan.id).desc())
        .all()
    )

    items = [DistributionItem(name=row.market, value=row.count) for row in rows]
    result = DistributionResponse(items=items)
    _cache_set(cache_key, result.model_dump_json(), CACHE_TTL)
    return result


# ═══════════════════════════════════════════
# Dashboard 聚合（BI看板主数据）
# ═══════════════════════════════════════════

@router.get("/dashboard")
def bi_dashboard(
    start_month: Optional[str] = Query(None, description="开始月份 YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月份 YYYY-MM"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """BI分析仪表盘 — 用原生SQL聚合（避免ORM lazy loading问题）

    支持按月份范围筛选策划趋势。
    """
    import json
    from sqlalchemy import text as sa_text

    cache_key = f"bi:dashboard:{start_month or ''}:{end_month or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return json.loads(cached)

    # ── 1. KPI: 原生SQL直接查询（不按日期筛选，KPI始终全量） ──
    total_plans = db.execute(sa_text(
        "SELECT COUNT(*) FROM product_plans"
    )).scalar() or 0

    completed_plans = db.execute(sa_text(
        "SELECT COUNT(*) FROM product_plans WHERE status IN ('approved', 'released')"
    )).scalar() or 0

    approval_rate = round(completed_plans / total_plans, 3) if total_plans > 0 else 0

    cost_overrun_count = db.execute(sa_text(
        "SELECT COUNT(*) FROM alert_events WHERE is_resolved = 0"
    )).scalar() or 0

    kpi = {
        "total_plans": total_plans,
        "approval_rate": approval_rate,
        "cost_overrun_count": cost_overrun_count,
    }

    # ── 2. 策划月度趋势（支持日期筛选） ──
    trend_sql = "SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS count FROM product_plans"
    params: list = []
    if start_month:
        trend_sql += " WHERE strftime('%Y-%m', created_at) >= ?"
        params.append(start_month)
    if end_month:
        trend_sql += " AND strftime('%Y-%m', created_at) <= ?" if start_month else " WHERE strftime('%Y-%m', created_at) <= ?"
        params.append(end_month)
    trend_sql += " GROUP BY month ORDER BY month LIMIT 12"

    trend_rows = db.execute(sa_text(trend_sql), params).fetchall()
    planning_trend = [{"month": row[0], "count": row[1]} for row in trend_rows]

    # ── 3. 成本超标 Top5 ──
    alert_rows = db.execute(sa_text(
        "SELECT plan_name, target_amount, actual_amount, "
        "variance_amount, variance_pct, alert_level "
        "FROM alert_events WHERE is_resolved = 0 "
        "ORDER BY ABS(variance_pct) DESC LIMIT 5"
    )).fetchall()
    cost_overrun_top5 = [
        {
            "project_name": row[0] or "未知项目",
            "budget": float(row[1] or 0),
            "actual": float(row[2] or 0),
            "overrun_rate": float(row[4] or 0) / 100,
            "overrun_amount": float(row[3] or 0),
            "alert_level": row[5] or "warning",
        }
        for row in alert_rows
    ]

    result = {
        "kpi": kpi,
        "planning_trend": planning_trend,
        "cost_overrun_top5": cost_overrun_top5,
    }

    _cache_set(cache_key, json.dumps(result, ensure_ascii=False), CACHE_TTL)
    return result


# ── 成本分析端点已拆分到 bi_cost_analytics.py ──


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
