"""BI成本分析API — 从bi_analytics.py拆分（成本维度统计/预算执行/效率趋势/超标排行）"""
from datetime import date
from typing import Optional
import json
import logging
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_menu
from app.models.product_plan import ProductPlan, ProductPlanProjectLink
from app.models.project import Project
from app.models.user import User
from app.models.cost_accounting import CostAccountingSheet, SheetStatus, CostAccountingPeriod
from app.models.cost_recalculation import CostRecalculationResult as CRR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bi", tags=["BI分析看板"])
_redis_pool: Optional['redis.ConnectionPool'] = None
CACHE_TTL = 600  # 10分钟

def _redis_client() -> Optional['redis.Redis']:
    """尝试获取Redis连接，失败返回None"""
    global _redis_pool
    try:
        import redis as _redis
        if _redis_pool is None:
            _redis_pool = _redis.ConnectionPool(host="127.0.0.1", port=6379, socket_connect_timeout=1, decode_responses=True)
        return _redis.Redis(connection_pool=_redis_pool)
    except Exception:
        return None

def _cache_get(key: str) -> Optional[str]:
    """从Redis读取缓存"""
    try:
        r = _redis_client()
        return None if r is None else r.get(key)
    except Exception:
        return None

def _cache_set(key: str, value: str, ttl: int = CACHE_TTL) -> None:
    """写入Redis缓存"""
    try:
        r = _redis_client()
        if r is not None:
            r.setex(key, ttl, value)
    except Exception:
        pass

@router.get("/cost")
def bi_cost(top_n: int = Query(10, ge=1, le=100), year: Optional[int] = Query(None), db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> dict:
    """成本维度聚合统计：预算执行率 / 超标项目TopN"""
    sheet_base = db.query(CostAccountingSheet).filter(CostAccountingSheet.status == SheetStatus.FINALIZED)
    if year:
        sheet_base = sheet_base.filter(func.extract("YEAR", CostAccountingSheet.created_at) == year)
    agg = sheet_base.with_entities(
        func.sum(CostAccountingSheet.total_cost_target).label("total_target"),
        func.sum(CostAccountingSheet.total_cost_actual).label("total_actual"),
        func.sum(CostAccountingSheet.variance_amount).label("total_variance"),
        func.avg(CostAccountingSheet.variance_pct).label("avg_variance_pct"),
        func.count(CostAccountingSheet.id).label("sheet_count"),
    ).first()
    total_target = agg.total_target or 0
    total_actual = agg.total_actual or 0
    result = {"budget_execution": {
        "total_target": round(total_target, 2), "total_actual": round(total_actual, 2),
        "execution_rate": round(total_actual / total_target * 100, 2) if total_target > 0 else 0,
        "total_variance": round(agg.total_variance or 0, 2), "avg_variance_pct": round(agg.avg_variance_pct or 0, 2),
        "sheet_count": agg.sheet_count or 0,
    }}
    top_rows = sheet_base.with_entities(
        CostAccountingSheet.sheet_no, CostAccountingSheet.product_plan_id,
        CostAccountingSheet.total_cost_target, CostAccountingSheet.total_cost_actual,
        CostAccountingSheet.variance_amount, CostAccountingSheet.variance_pct,
        ProductPlan.name.label("plan_name"), ProductPlan.series.label("plan_series"),
    ).join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id
    ).filter(CostAccountingSheet.variance_pct > 0
    ).order_by(CostAccountingSheet.variance_amount.desc()).limit(top_n).all()
    result["over_budget_topn"] = [{
        "sheet_no": row.sheet_no, "product_plan_id": row.product_plan_id,
        "plan_name": row.plan_name, "plan_series": row.plan_series,
        "cost_target": round(row.total_cost_target, 2), "cost_actual": round(row.total_cost_actual, 2),
        "variance_amount": round(row.variance_amount, 2), "variance_pct": round(row.variance_pct, 2),
    } for row in top_rows]
    proj_base = db.query(Project).filter(Project.is_deleted == False, Project.budget.isnot(None), Project.budget > 0)
    if year:
        proj_base = proj_base.filter(func.extract("YEAR", Project.created_at) == year)
    budget_agg = proj_base.with_entities(
        func.sum(Project.budget).label("total_budget"), func.count(Project.id).label("project_count"),
    ).first()
    actual_spend = db.query(func.sum(CostAccountingSheet.total_cost_actual)
    ).join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id
    ).join(ProductPlanProjectLink, ProductPlanProjectLink.product_plan_id == ProductPlan.id
    ).join(Project, Project.id == ProductPlanProjectLink.project_id
    ).filter(Project.is_deleted == False, Project.budget.isnot(None), Project.budget > 0,
             CostAccountingSheet.status == SheetStatus.FINALIZED).scalar() or 0
    total_budget = budget_agg.total_budget or 0
    result["project_budget"] = {
        "total_budget": round(total_budget, 2), "total_spent": round(actual_spend, 2),
        "execution_rate": round(actual_spend / total_budget * 100, 2) if total_budget > 0 else 0,
        "project_count": budget_agg.project_count or 0,
    }
    return result

@router.get("/cost-efficiency")
def bi_cost_efficiency(limit_periods: int = Query(12, ge=1, le=48), min_score: float = Query(0, ge=0, le=100), db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> dict:
    """成本效率趋势 — 按核算期间+BTU段分组"""
    from sqlalchemy import func as sa_func
    cache_key = f"bi:cost-efficiency:periods={limit_periods}:min={min_score}"
    cached = _cache_get(cache_key)
    if cached is not None: return json.loads(cached)
    periods = db.query(CostAccountingPeriod.id, CostAccountingPeriod.period_name
    ).filter(CostAccountingPeriod.status.in_(["active", "closed"])
    ).order_by(CostAccountingPeriod.start_date.desc()).limit(limit_periods).all()
    if not periods:
        empty = {"periods": [], "series": [], "summary": {}}
        _cache_set(cache_key, json.dumps(empty), CACHE_TTL)
        return empty
    period_ids = [p.id for p in periods]
    period_names = {p.id: p.period_name for p in periods}
    rows = db.query(
        CRR.period_id, CRR.capacity_key,
        sa_func.count(CRR.id).label("product_count"),
        sa_func.avg(CRR.cost_efficiency_score).label("avg_score"),
        sa_func.avg(CRR.variance_pct).label("avg_variance_pct"),
    ).filter(CRR.period_id.in_(period_ids), CRR.status == "completed", CRR.cost_efficiency_score >= min_score
    ).group_by(CRR.period_id, CRR.capacity_key).order_by(CRR.period_id, CRR.capacity_key).all()
    periods_sorted = sorted(periods, key=lambda p: p.id)
    btu_data = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        pid, cap_key = r.period_id, r.capacity_key or "未知"
        btu_data[cap_key][pid] = {
            "period_name": period_names.get(pid, f"Period#{pid}"),
            "avg_score": round(float(r.avg_score or 0), 1),
            "product_count": int(r.product_count),
            "avg_variance_pct": round(float(r.avg_variance_pct or 0), 1),
        }
    series = []
    for cap_key in sorted(btu_data.keys()):
        data_points = [btu_data[cap_key][p.id] for p in periods_sorted if p.id in btu_data[cap_key]]
        if data_points:
            series.append({"capacity_key": cap_key, "data": data_points})
    all_scores = [float(r.avg_score or 0) for r in rows]
    result = {
        "periods": [{"id": p.id, "name": period_names.get(p.id, f"Period#{p.id}")} for p in periods_sorted],
        "series": series,
        "summary": {
            "total_recalc_count": db.query(sa_func.count(CRR.id)).filter(CRR.status == "completed", CRR.period_id.in_(period_ids)).scalar() or 0,
            "periods_with_data": len(set(r.period_id for r in rows)),
            "btu_segments_with_data": len(series),
            "overall_avg_score": round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
        },
    }
    _cache_set(cache_key, json.dumps(result), CACHE_TTL)
    return result

@router.get("/cost/budget-vs-actual")
def bi_cost_budget_vs_actual(year: Optional[int] = Query(None), db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> dict:
    """预算 vs 实际对比"""
    sheet_base = db.query(CostAccountingSheet).filter(CostAccountingSheet.status == SheetStatus.FINALIZED)
    if year:
        sheet_base = sheet_base.filter(func.extract("YEAR", CostAccountingSheet.created_at) == year)
    items = sheet_base.all()
    return {"labels": [s.product_name or f"项目#{s.id}" for s in items], "budget": [float(s.target_total or 0) for s in items], "actual": [float(s.actual_total or 0) for s in items]}

@router.get("/cost/dashboard")
def bi_cost_dashboard(period_limit: int = Query(12, ge=1, le=48), min_score: float = Query(0, ge=0, le=100), db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> dict:
    """多维度成本分析看板 — KPI汇总/逐期间趋势/系列分布/排名/直方图"""
    import json as _json
    from sqlalchemy import func as sa_func
    cache_key = f"bi:cost-dashboard:p={period_limit}:m={min_score}"
    cached = _cache_get(cache_key)
    if cached is not None: return _json.loads(cached)
    periods = db.query(CostAccountingPeriod.id, CostAccountingPeriod.period_name, CostAccountingPeriod.start_date
    ).filter(CostAccountingPeriod.status.in_(["active", "closed"])
    ).order_by(CostAccountingPeriod.start_date.desc()).limit(period_limit).all()
    if not periods:
        empty = {"kpi": {}, "trend_by_period": [], "series_breakdown": [], "ranking": [], "distribution": []}
        _cache_set(cache_key, _json.dumps(empty), CACHE_TTL)
        return empty
    period_ids = [p.id for p in periods]
    period_names = {p.id: p.period_name for p in periods}
    completed = db.query(CRR).filter(CRR.status == "completed", CRR.period_id.in_(period_ids)).all()
    all_scores = [r.cost_efficiency_score for r in completed if r.cost_efficiency_score > 0]
    product_count = len(all_scores)
    avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    trend_direction = "flat"
    if len(periods) >= 2:
        avg0 = db.query(sa_func.avg(CRR.cost_efficiency_score)).filter(CRR.period_id == periods[0].id, CRR.status == "completed").scalar() or 0
        avg1 = db.query(sa_func.avg(CRR.cost_efficiency_score)).filter(CRR.period_id == periods[1].id, CRR.status == "completed").scalar() or 0
        diff = float(avg0) - float(avg1)
        trend_direction = "up" if diff > 2 else "down" if diff < -2 else "flat"
    kpi = {"avg_score": avg_score, "highest_score": round(max(all_scores), 1) if all_scores else 0,
           "lowest_score": round(min(all_scores), 1) if all_scores else 0,
           "product_count": product_count, "low_efficiency_count": sum(1 for s in all_scores if s < 60),
           "trend_direction": trend_direction}
    trend_rows = db.query(CRR.period_id, sa_func.count(CRR.id).label("cnt"),
        sa_func.avg(CRR.cost_efficiency_score).label("avg_sc"), sa_func.avg(CRR.variance_pct).label("avg_var")
    ).filter(CRR.status == "completed", CRR.period_id.in_(period_ids), CRR.cost_efficiency_score >= min_score
    ).group_by(CRR.period_id).order_by(CRR.period_id).all()
    periods_sorted = sorted(periods, key=lambda p: p.id)
    trend_by_period = []
    for p in periods_sorted:
        match = next((r for r in trend_rows if r.period_id == p.id), None)
        if match:
            trend_by_period.append({"period_id": p.id, "period_name": period_names.get(p.id, f"#{p.id}"),
                "avg_score": round(float(match.avg_sc or 0), 1), "product_count": int(match.cnt),
                "avg_variance_pct": round(float(match.avg_var or 0), 1)})
    series_rows = db.query(ProductPlan.series, sa_func.count(CRR.id).label("cnt"),
        sa_func.avg(CRR.actual_bom_cost).label("avg_cost"), sa_func.avg(CRR.cost_efficiency_score).label("avg_sc"),
        sa_func.avg(CRR.variance_pct).label("avg_var")
    ).join(ProductPlan, ProductPlan.id == CRR.product_plan_id
    ).filter(CRR.status == "completed", CRR.period_id.in_(period_ids), CRR.cost_efficiency_score >= min_score,
             ProductPlan.series.isnot(None), ProductPlan.series != ""
    ).group_by(ProductPlan.series).order_by(sa_func.count(CRR.id).desc()).all()
    series_breakdown = [{"series": r.series, "product_count": int(r.cnt), "avg_cost": round(float(r.avg_cost or 0), 2),
        "avg_score": round(float(r.avg_sc or 0), 1), "avg_variance_pct": round(float(r.avg_var or 0), 1)} for r in series_rows]
    ranking_query = db.query(CRR.product_plan_id, ProductPlan.name.label("plan_name"),
        ProductPlan.series.label("plan_series"), CRR.cost_efficiency_score, CRR.variance_pct,
        CRR.matched_btu, CRR.period_id, CRR.actual_bom_cost, CRR.baseline_material_cost
    ).join(ProductPlan, ProductPlan.id == CRR.product_plan_id
    ).filter(CRR.status == "completed", CRR.period_id.in_(period_ids), CRR.cost_efficiency_score >= min_score)
    top10 = ranking_query.order_by(CRR.cost_efficiency_score.desc()).limit(10).all()
    bottom10 = ranking_query.order_by(CRR.cost_efficiency_score.asc()).limit(10).all()
    def _ranking_item(row):
        return {"product_plan_id": row.product_plan_id, "plan_name": row.plan_name or "未知产品",
            "plan_series": row.plan_series or "-", "cost_efficiency_score": round(float(row.cost_efficiency_score), 1),
            "variance_pct": round(float(row.variance_pct or 0), 1), "matched_btu": row.matched_btu or "-",
            "period_name": period_names.get(row.period_id, f"#{row.period_id}"),
            "actual_cost": round(float(row.actual_bom_cost or 0), 2), "baseline_cost": round(float(row.baseline_material_cost or 0), 2)}
    ranking = {"top": [_ranking_item(r) for r in top10], "bottom": [_ranking_item(r) for r in bottom10]}
    bins = []
    for i in range(0, 100, 10):
        lo, hi = i, i + 10
        cnt = db.query(sa_func.count(CRR.id)).filter(CRR.status == "completed", CRR.period_id.in_(period_ids),
            CRR.cost_efficiency_score >= lo, CRR.cost_efficiency_score < hi).scalar() or 0
        bins.append({"range": f"{lo}-{hi}", "range_label": f"{lo}~{hi}分", "count": cnt, "low": lo, "high": hi})
    cnt_100 = db.query(sa_func.count(CRR.id)).filter(CRR.status == "completed", CRR.period_id.in_(period_ids),
        CRR.cost_efficiency_score == 100).scalar() or 0
    if cnt_100 > 0:
        bins.append({"range": "100", "range_label": "100分", "count": cnt_100, "low": 100, "high": 100})
    result = {"kpi": kpi, "trend_by_period": trend_by_period, "series_breakdown": series_breakdown, "ranking": ranking, "distribution": bins}
    _cache_set(cache_key, _json.dumps(result, ensure_ascii=False), CACHE_TTL)
    return result

@router.get("/cost/department-ratio")
def bi_cost_department_ratio(start_month: Optional[str] = Query(None), end_month: Optional[str] = Query(None), db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> list:
    """成本部门占比 — 按创建者关联部门聚合"""
    rows = db.query(User.department.label("name"), func.sum(CostAccountingSheet.total_cost_actual).label("value")
    ).join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id
    ).join(User, User.username == ProductPlan.created_by
    ).filter(CostAccountingSheet.status.in_(["finalized", "active"]))
    if start_month: rows = rows.filter(CostAccountingSheet.created_at >= start_month)
    if end_month: rows = rows.filter(CostAccountingSheet.created_at <= end_month)
    rows = rows.group_by(User.department).order_by(func.sum(CostAccountingSheet.total_cost_actual).desc()).all()
    return [{"name": r.name or "未分配", "value": round(r.value, 2)} for r in rows]

@router.get("/cost/over-budget")
def bi_cost_over_budget(start_month: Optional[str] = Query(None), end_month: Optional[str] = Query(None), db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> list:
    """超标项目列表"""
    q = db.query(CostAccountingSheet
    ).join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id
    ).filter(CostAccountingSheet.status.in_(["finalized", "active"]), CostAccountingSheet.variance_pct > 0)
    if start_month: q = q.filter(CostAccountingSheet.created_at >= start_month)
    if end_month: q = q.filter(CostAccountingSheet.created_at <= end_month)
    rows = q.order_by(CostAccountingSheet.variance_amount.desc()).limit(50).all()
    return [{"department": (db.query(User.department).join(ProductPlan, ProductPlan.created_by == User.username).filter(ProductPlan.id == r.product_plan_id).scalar()) or "",
        "category": r.sheet_no or "", "budget": round(r.total_cost_target or 0, 2),
        "actual": round(r.total_cost_actual or 0, 2), "rate": round(r.variance_pct or 0, 2),
        "gap": round(r.variance_amount or 0, 2)} for r in rows]

@router.get("/cost/departments")
def bi_cost_departments(db: Session = Depends(get_db), _=Depends(require_menu("bi-analytics"))) -> list:
    """获取所有已使用的部门列表"""
    depts = db.query(User.department).filter(User.department.isnot(None), User.department != ""
    ).distinct().order_by(User.department).all()
    return [d[0] for d in depts] if depts else ["研发部", "市场部", "生产部", "质量部", "供应链", "采购部", "工艺部"]
