"""BI分析看板 — 数据聚合API

全部查询走SQL聚合（避免全表扫描）。
权限: require_menu("bi-analytics")

索引优化建议:
  1. product_plans 表: 联合索引 (status, created_at) 加速趋势+漏斗查询
  2. product_plans 表: 索引 (market) 加速市场分布查询
"""
from datetime import date, datetime, timedelta
from typing import Optional, Any
import json
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_menu
from app.models.product_plan import ProductPlan, ProductPlanStage, ProductPlanProjectLink
from app.models.project import Project, ProjectGate
from app.models.approval import ApprovalRequest, ApprovalRecord
from app.models.cost_accounting import CostAccountingSheet, SheetStatus
from app.models.cost_recalculation import CostRecalculationResult
from app.schemas.bi import TrendItem, TrendResponse, FunnelItem, FunnelResponse, DistributionItem, DistributionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bi", tags=["BI分析看板"])


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
        return None


def _cache_set(key: str, value: str, ttl: int = 600) -> None:
    """写入 Redis 缓存，失败静默忽略"""
    try:
        r = _redis_client()
        if r is None:
            return
        r.setex(key, ttl, value)
    except Exception:
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
# 成本维度统计
# ═══════════════════════════════════════════

@router.get("/cost")
def bi_cost(
    top_n: int = Query(10, description="超标项目Top N", ge=1, le=100),
    year: Optional[int] = Query(None, description="筛选年份"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
) -> dict:
    """成本维度聚合统计

    返回: 预算执行率 / 超标项目TopN
    """
    sheet_base = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.status == SheetStatus.FINALIZED,
    )
    if year:
        sheet_base = sheet_base.filter(
            func.extract("YEAR", CostAccountingSheet.created_at) == year
        )

    # ── 1. 预算执行率（总实际 / 总目标） ──
    agg = (
        sheet_base
        .with_entities(
            func.sum(CostAccountingSheet.total_cost_target).label("total_target"),
            func.sum(CostAccountingSheet.total_cost_actual).label("total_actual"),
            func.sum(CostAccountingSheet.variance_amount).label("total_variance"),
            func.avg(CostAccountingSheet.variance_pct).label("avg_variance_pct"),
            func.count(CostAccountingSheet.id).label("sheet_count"),
        )
        .first()
    )

    total_target = agg.total_target or 0
    total_actual = agg.total_actual or 0
    result = {
        "budget_execution": {
            "total_target": round(total_target, 2),
            "total_actual": round(total_actual, 2),
            "execution_rate": round(
                total_actual / total_target * 100, 2
            ) if total_target > 0 else 0,
            "total_variance": round(agg.total_variance or 0, 2),
            "avg_variance_pct": round(agg.avg_variance_pct or 0, 2),
            "sheet_count": agg.sheet_count or 0,
        },
    }

    # ── 2. 超标项目 TopN ──
    # 从 cost_accounting_sheets 关联 product_plans 获取名称
    top_rows = (
        sheet_base
        .with_entities(
            CostAccountingSheet.sheet_no,
            CostAccountingSheet.product_plan_id,
            CostAccountingSheet.total_cost_target,
            CostAccountingSheet.total_cost_actual,
            CostAccountingSheet.variance_amount,
            CostAccountingSheet.variance_pct,
            ProductPlan.name.label("plan_name"),
            ProductPlan.series.label("plan_series"),
        )
        .join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id)
        .filter(CostAccountingSheet.variance_pct > 0)
        .order_by(CostAccountingSheet.variance_amount.desc())
        .limit(top_n)
        .all()
    )

    result["over_budget_topn"] = [
        {
            "sheet_no": row.sheet_no,
            "product_plan_id": row.product_plan_id,
            "plan_name": row.plan_name,
            "plan_series": row.plan_series,
            "cost_target": round(row.total_cost_target, 2),
            "cost_actual": round(row.total_cost_actual, 2),
            "variance_amount": round(row.variance_amount, 2),
            "variance_pct": round(row.variance_pct, 2),
        }
        for row in top_rows
    ]

    # ── 3. 项目预算执行率（从 projects 表的 budget 字段） ──
    proj_base = db.query(Project).filter(
        Project.is_deleted == False,
        Project.budget.isnot(None),
        Project.budget > 0,
    )
    if year:
        proj_base = proj_base.filter(
            func.extract("YEAR", Project.created_at) == year
        )

    # 实际花费需要从 cost_accounting_sheets 关联
    # projects → product_plans → cost_accounting_sheets
    budget_agg = (
        proj_base
        .with_entities(
            func.sum(Project.budget).label("total_budget"),
            func.count(Project.id).label("project_count"),
        )
        .first()
    )

    # 获取实际总花费（关联查询）
    actual_spend = (
        db.query(func.sum(CostAccountingSheet.total_cost_actual))
        .join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id)
        .join(ProductPlanProjectLink, ProductPlanProjectLink.product_plan_id == ProductPlan.id)
        .join(Project, Project.id == ProductPlanProjectLink.project_id)
        .filter(
            Project.is_deleted == False,
            Project.budget.isnot(None),
            Project.budget > 0,
            CostAccountingSheet.status == SheetStatus.FINALIZED,
        )
        .scalar() or 0
    )

    total_budget = budget_agg.total_budget or 0
    result["project_budget"] = {
        "total_budget": round(total_budget, 2),
        "total_spent": round(actual_spend, 2),
        "execution_rate": round(
            actual_spend / total_budget * 100, 2
        ) if total_budget > 0 else 0,
        "project_count": budget_agg.project_count or 0,
    }

    return result


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
# 成本效率趋势
# ═══════════════════════════════════════════

@router.get("/cost-efficiency")
def bi_cost_efficiency(
    limit_periods: int = Query(12, ge=1, le=48, description="最近N个核算期间"),
    min_score: float = Query(0, ge=0, le=100, description="最低评分筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """成本效率趋势 — 按核算期间+BTU段分组

    返回每个期间各BTU段的平均效率评分/产品数/平均差异率
    用于前端ECharts折线图（各BTU段为不同系列）
    """
    from app.models.cost_accounting import CostAccountingPeriod
    from app.models.cost_recalculation import CostRecalculationResult as CRR
    from sqlalchemy import func as sa_func

    cache_key = f"bi:cost-efficiency:periods={limit_periods}:min={min_score}"
    cached = _cache_get(cache_key)
    if cached is not None:
        import json
        return json.loads(cached)

    # 获取最近的 period_id 列表
    periods = (
        db.query(CostAccountingPeriod.id, CostAccountingPeriod.period_name)
        .filter(CostAccountingPeriod.status.in_(["active", "closed"]))
        .order_by(CostAccountingPeriod.start_date.desc())
        .limit(limit_periods)
        .all()
    )
    if not periods:
        result = {"periods": [], "series": [], "summary": {}}
        _cache_set(cache_key, json.dumps(result), CACHE_TTL)
        return result

    period_ids = [p.id for p in periods]
    period_names = {p.id: p.period_name for p in periods}

    # 按 period + capacity_key 分组聚合
    rows = (
        db.query(
            CRR.period_id,
            CRR.capacity_key,
            sa_func.count(CRR.id).label("product_count"),
            sa_func.avg(CRR.cost_efficiency_score).label("avg_score"),
            sa_func.avg(CRR.variance_pct).label("avg_variance_pct"),
            sa_func.min(CRR.cost_efficiency_score).label("min_score"),
            sa_func.max(CRR.cost_efficiency_score).label("max_score"),
        )
        .filter(
            CRR.period_id.in_(period_ids),
            CRR.status == "completed",
            CRR.cost_efficiency_score >= min_score,
        )
        .group_by(CRR.period_id, CRR.capacity_key)
        .order_by(CRR.period_id, CRR.capacity_key)
        .all()
    )

    # 整理为前端友好格式
    # periods: 按时序排列的期间列表
    # series: 每个 BTU 段一条线
    from collections import defaultdict

    periods_sorted = sorted(periods, key=lambda p: p.id)
    btu_data = defaultdict(lambda: defaultdict(dict))

    for r in rows:
        pid = r.period_id
        cap_key = r.capacity_key or "未知"
        btu_data[cap_key][pid] = {
            "period_name": period_names.get(pid, f"Period#{pid}"),
            "avg_score": round(float(r.avg_score or 0), 1),
            "product_count": int(r.product_count),
            "avg_variance_pct": round(float(r.avg_variance_pct or 0), 1),
            "min_score": round(float(r.min_score or 0), 1),
            "max_score": round(float(r.max_score or 0), 1),
        }

    series = []
    for cap_key in sorted(btu_data.keys()):
        data_points = []
        for p in periods_sorted:
            point = btu_data[cap_key].get(p.id, None)
            if point:
                data_points.append(point)
        if data_points:  # 只返回有数据的系列
            series.append({
                "capacity_key": cap_key,
                "data": data_points,
            })

    # 汇总统计
    all_scores = [float(r.avg_score or 0) for r in rows]
    total = db.query(sa_func.count(CRR.id)).filter(
        CRR.status == "completed",
        CRR.period_id.in_(period_ids),
    ).scalar() or 0

    summary = {
        "total_recalc_count": total,
        "periods_with_data": len(set(r.period_id for r in rows)),
        "btu_segments_with_data": len(series),
        "overall_avg_score": round(
            sum(all_scores) / len(all_scores), 1
        ) if all_scores else 0,
    }

    result = {
        "periods": [
            {"id": p.id, "name": period_names.get(p.id, f"Period#{p.id}")}
            for p in periods_sorted
        ],
        "series": series,
        "summary": summary,
    }

    _cache_set(cache_key, json.dumps(result), CACHE_TTL)
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
    trend_sql = "SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) AS count FROM product_plans"
    params: list = []
    if start_month:
        trend_sql += " WHERE DATE_FORMAT(created_at, '%Y-%m') >= ?"
        params.append(start_month)
    if end_month:
        trend_sql += " AND DATE_FORMAT(created_at, '%Y-%m') <= ?" if start_month else " WHERE DATE_FORMAT(created_at, '%Y-%m') <= ?"
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


# ═══════════════════════════════════════════
# 多维度成本分析看板
# ═══════════════════════════════════════════


@router.get("/cost/dashboard")
def bi_cost_dashboard(
    period_limit: int = Query(12, ge=1, le=48, description="最近N个核算期间"),
    min_score: float = Query(0, ge=0, le=100, description="最低评分筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """多维度成本分析看板

    在一个聚合端点中返回：
      - KPI 汇总（平均分/最高/最低/产品数/低效数/趋势方向）
      - 逐期间趋势（每期的平均评分/产品数/平均差异率）
      - 产品系列成本分布（每系列的产品数/平均成本/平均评分）
      - 产品效率排名（Top/Bottom 各10条）
      - 评分分布直方图（10个分桶）
    """
    import json as _json
    from app.models.cost_accounting import CostAccountingPeriod
    from app.models.cost_recalculation import CostRecalculationResult as CRR
    from app.models.product_plan import ProductPlan
    from sqlalchemy import func as sa_func, cast, Integer

    cache_key = f"bi:cost-dashboard:p={period_limit}:m={min_score}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return _json.loads(cached)

    # ── 1. 获取最近 period_ids ──
    periods = (
        db.query(CostAccountingPeriod.id, CostAccountingPeriod.period_name, CostAccountingPeriod.start_date)
        .filter(CostAccountingPeriod.status.in_(["active", "closed"]))
        .order_by(CostAccountingPeriod.start_date.desc())
        .limit(period_limit)
        .all()
    )
    if not periods:
        empty = {"kpi": {}, "trend_by_period": [], "series_breakdown": [], "ranking": [], "distribution": []}
        _cache_set(cache_key, _json.dumps(empty), CACHE_TTL)
        return empty

    period_ids = [p.id for p in periods]
    period_names = {p.id: p.period_name for p in periods}

    # ── 2. KPI 汇总 ──
    completed = (
        db.query(CRR)
        .filter(CRR.status == "completed", CRR.period_id.in_(period_ids))
        .all()
    )
    all_scores = [r.cost_efficiency_score for r in completed if r.cost_efficiency_score > 0]
    product_count = len(all_scores)
    low_count = sum(1 for s in all_scores if s < 60)
    avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    highest = round(max(all_scores), 1) if all_scores else 0
    lowest = round(min(all_scores), 1) if all_scores else 0

    # 趋势方向：比较最近2期平均分
    trend_direction = "flat"
    if len(periods) >= 2:
        p0 = periods[0].id
        p1 = periods[1].id
        avg0 = (
            db.query(sa_func.avg(CRR.cost_efficiency_score))
            .filter(CRR.period_id == p0, CRR.status == "completed")
            .scalar() or 0
        )
        avg1 = (
            db.query(sa_func.avg(CRR.cost_efficiency_score))
            .filter(CRR.period_id == p1, CRR.status == "completed")
            .scalar() or 0
        )
        diff = float(avg0 or 0) - float(avg1 or 0)
        if diff > 2:
            trend_direction = "up"
        elif diff < -2:
            trend_direction = "down"
        else:
            trend_direction = "flat"

    kpi = {
        "avg_score": avg_score,
        "highest_score": highest,
        "lowest_score": lowest,
        "product_count": product_count,
        "low_efficiency_count": low_count,
        "trend_direction": trend_direction,
    }

    # ── 3. 逐期间趋势 ──
    trend_rows = (
        db.query(
            CRR.period_id,
            sa_func.count(CRR.id).label("cnt"),
            sa_func.avg(CRR.cost_efficiency_score).label("avg_sc"),
            sa_func.avg(CRR.variance_pct).label("avg_var"),
        )
        .filter(CRR.status == "completed", CRR.period_id.in_(period_ids), CRR.cost_efficiency_score >= min_score)
        .group_by(CRR.period_id)
        .order_by(CRR.period_id)
        .all()
    )
    periods_sorted = sorted(periods, key=lambda p: p.id)
    trend_by_period = []
    period_score_map = {}
    for p in periods_sorted:
        match = None
        for r in trend_rows:
            if r.period_id == p.id:
                match = r
                break
        if match:
            trend_by_period.append({
                "period_id": p.id,
                "period_name": period_names.get(p.id, f"#{p.id}"),
                "avg_score": round(float(match.avg_sc or 0), 1),
                "product_count": int(match.cnt),
                "avg_variance_pct": round(float(match.avg_var or 0), 1),
            })
            period_score_map[p.id] = round(float(match.avg_sc or 0), 1)

    # ── 4. 产品系列成本分布 ──
    # 关联 CRR → CostAccountingSheet → ProductPlan 获取 series
    series_rows = (
        db.query(
            ProductPlan.series,
            sa_func.count(CRR.id).label("cnt"),
            sa_func.avg(CRR.actual_bom_cost).label("avg_cost"),
            sa_func.avg(CRR.cost_efficiency_score).label("avg_sc"),
            sa_func.avg(CRR.variance_pct).label("avg_var"),
        )
        .join(ProductPlan, ProductPlan.id == CRR.product_plan_id)
        .filter(
            CRR.status == "completed",
            CRR.period_id.in_(period_ids),
            CRR.cost_efficiency_score >= min_score,
            ProductPlan.series.isnot(None),
            ProductPlan.series != "",
        )
        .group_by(ProductPlan.series)
        .order_by(sa_func.count(CRR.id).desc())
        .all()
    )
    series_breakdown = [
        {
            "series": r.series,
            "product_count": int(r.cnt),
            "avg_cost": round(float(r.avg_cost or 0), 2),
            "avg_score": round(float(r.avg_sc or 0), 1),
            "avg_variance_pct": round(float(r.avg_var or 0), 1),
        }
        for r in series_rows
    ]

    # ── 5. 产品效率排名 ──
    # Top 10 (highest score) + Bottom 10 (lowest score)
    ranking_query = (
        db.query(
            CRR.product_plan_id,
            ProductPlan.name.label("plan_name"),
            ProductPlan.series.label("plan_series"),
            CRR.cost_efficiency_score,
            CRR.variance_pct,
            CRR.matched_btu,
            CRR.period_id,
            CRR.actual_bom_cost,
            CRR.baseline_material_cost,
        )
        .join(ProductPlan, ProductPlan.id == CRR.product_plan_id)
        .filter(
            CRR.status == "completed",
            CRR.period_id.in_(period_ids),
            CRR.cost_efficiency_score >= min_score,
        )
    )
    top10 = ranking_query.order_by(CRR.cost_efficiency_score.desc()).limit(10).all()
    bottom10 = ranking_query.order_by(CRR.cost_efficiency_score.asc()).limit(10).all()

    def _ranking_item(row):
        return {
            "product_plan_id": row.product_plan_id,
            "plan_name": row.plan_name or "未知产品",
            "plan_series": row.plan_series or "-",
            "cost_efficiency_score": round(float(row.cost_efficiency_score), 1),
            "variance_pct": round(float(row.variance_pct or 0), 1),
            "matched_btu": row.matched_btu or "-",
            "period_name": period_names.get(row.period_id, f"#{row.period_id}"),
            "actual_cost": round(float(row.actual_bom_cost or 0), 2),
            "baseline_cost": round(float(row.baseline_material_cost or 0), 2),
        }

    ranking = {
        "top": [_ranking_item(r) for r in top10],
        "bottom": [_ranking_item(r) for r in bottom10],
    }

    # ── 6. 评分分布直方图 ──
    # 按每10分为一桶: 0-10, 10-20, ..., 90-100
    bins = []
    for i in range(0, 100, 10):
        lo, hi = i, i + 10
        cnt = (
            db.query(sa_func.count(CRR.id))
            .filter(
                CRR.status == "completed",
                CRR.period_id.in_(period_ids),
                CRR.cost_efficiency_score >= lo,
                CRR.cost_efficiency_score < hi,
            )
            .scalar() or 0
        )
        bins.append({"range": f"{lo}-{hi}", "range_label": f"{lo}~{hi}分", "count": cnt, "low": lo, "high": hi})

    # 100分精确匹配
    cnt_100 = (
        db.query(sa_func.count(CRR.id))
        .filter(
            CRR.status == "completed",
            CRR.period_id.in_(period_ids),
            CRR.cost_efficiency_score == 100,
        )
        .scalar() or 0
    )
    if cnt_100 > 0:
        bins.append({"range": "100", "range_label": "100分", "count": cnt_100, "low": 100, "high": 100})

    result = {
        "kpi": kpi,
        "trend_by_period": trend_by_period,
        "series_breakdown": series_breakdown,
        "ranking": ranking,
        "distribution": bins,
    }

    _cache_set(cache_key, _json.dumps(result, ensure_ascii=False), CACHE_TTL)
    return result
