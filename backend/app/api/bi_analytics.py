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
