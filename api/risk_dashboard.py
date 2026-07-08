"""智能决策仪表盘 API — MQ/MRC/CDF 三合一聚合看板

提供物料风险、制造就绪度、认证需求的聚合查询接口，
供前端仪表盘组件渲染图表和卡片。

权限: pm, admin, general_manager
"""
from fastapi import APIRouter, Depends, HTTPException, Path

from app.core.security import require_role
from app.services.mq_service import get_all_risk_summary, get_plan_risk_detail
from app.services.mrc_service import get_all_mrc_summary, get_plan_mrc_detail
from app.services.cdf_service import get_cert_dashboard, get_plan_cert_detail

router = APIRouter(prefix="/v2/dashboard", tags=["智能决策仪表盘"])


@router.get("")
def dashboard_root():
    """仪表盘根路径 — 返回总体概览"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v2/dashboard/overview")


# ═══════════════════════════════════════════
# 物料风险 (MQ)
# ═══════════════════════════════════════════


@router.get("/mq-summary")
def dashboard_mq_summary(
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """物料风险总览 — 所有计划的高/中/低风险分布

    Returns:
        {
            "total_plans": int,
            "high_risk_count": int,
            "medium_risk_count": int,
            "low_risk_count": int,
            "plans": [{plan_id, risk_level, risk_score, total_items, high_risk_count}]
        }
    """
    try:
        return get_all_risk_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取物料风险总览失败: {e}")


@router.get("/mq-detail/{plan_id}")
def dashboard_mq_detail(
    plan_id: str = Path(..., description="产品策划ID"),
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """物料风险详情 — 单个计划的物料级风险明细

    返回完整评估结果，包含每项物料的独立风险等级。

    Args:
        plan_id: 产品策划ID

    Returns:
        {
            "plan_id": str,
            "risk_level": str,
            "risk_score": int,
            "total_items": int,
            "high_risk_count": int,
            "medium_risk_count": int,
            "low_risk_count": int,
            "high_risk_items": [{name, type, supplier, score}],
            "items": [{name, type, supplier, risk_level, score}],
            "recommendation": str,
        }
    """
    try:
        result = get_plan_risk_detail(plan_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取物料风险详情失败: {e}")


# ═══════════════════════════════════════════
# 制造就绪度 (MRC)
# ═══════════════════════════════════════════


@router.get("/mrc-summary")
def dashboard_mrc_summary(
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """制造就绪度总览 — 所有计划的就绪度评分汇总

    Returns:
        {
            "total_plans": int,
            "average_score": float,
            "ready_count": int,
            "partially_ready_count": int,
            "not_ready_count": int,
            "dimension_averages": {design, process, mold, supply: float},
            "plans": [{plan_id, overall_score, readiness_level, gaps}]
        }
    """
    try:
        return get_all_mrc_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取制造就绪度总览失败: {e}")


@router.get("/mrc-detail/{plan_id}")
def dashboard_mrc_detail(
    plan_id: str = Path(..., description="产品策划ID"),
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """制造就绪度详情 — 单个计划四维雷达评分

    返回设计、工艺、模具、供应四个维度的评分和差距分析。

    Args:
        plan_id: 产品策划ID

    Returns:
        {
            "plan_id": str,
            "overall_score": int,
            "readiness_level": str,
            "dimensions": {
                "design": {score, status, label},
                "process": {score, status, label},
                "mold": {score, status, label},
                "supply": {score, status, label},
            },
            "gaps": [str],
            "recommendation": str,
            "dimension_labels": {design, process, mold, supply: str}
        }
    """
    try:
        result = get_plan_mrc_detail(plan_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取制造就绪度详情失败: {e}")


# ═══════════════════════════════════════════
# 认证需求 (CDF)
# ═══════════════════════════════════════════


@router.get("/cdf-summary")
def dashboard_cdf_summary(
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """认证看板 — 各类型认证进度及强制认证完成率

    Returns:
        {
            "total_plans": int,
            "cert_type_summary": [
                {code, name, mandatory, required_plans_count, completed_count, completion_rate}
            ],
            "mandatory_completion_rate": float,
            "overall_risk_level": str,
            "average_lead_days": float,
        }
    """
    try:
        return get_cert_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取认证看板失败: {e}")


@router.get("/cdf-detail/{plan_id}")
def dashboard_cdf_detail(
    plan_id: str = Path(..., description="产品策划ID"),
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """认证详情 — 单个计划认证要求 + 推进时间线

    Args:
        plan_id: 产品策划ID

    Returns:
        {
            "plan_id": str,
            "product_type": str,
            "target_markets": [str],
            "required_certs": [{code, name, mandatory, lead_time_days}],
            "estimated_lead_days": int,
            "risk_level": str,
            "recommendation": str,
            "timeline": [{phase, code, name, lead_days, type, can_parallel}]
        }
    """
    try:
        result = get_plan_cert_detail(plan_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取认证详情失败: {e}")


# ═══════════════════════════════════════════
# 三合一总览
# ═══════════════════════════════════════════


@router.get("/overview")
def dashboard_overview(
    _=Depends(require_role("pm", "admin", "general_manager")),
) -> dict:
    """三合一总览面板 — 物料风险 + 制造就绪度 + 认证看板

    一次调用返回三个维度的摘要数据，供仪表盘首页渲染。
    每个服务独立 try/except，部分失败时仍返回可用数据 + errors 字段。

    Returns:
        {
            "mq": {total_plans, high_risk_count, medium_risk_count, low_risk_count} | {error},
            "mrc": {total_plans, average_score, ready_count, partially_ready_count, not_ready_count} | {error},
            "cdf": {total_plans, mandatory_completion_rate, overall_risk_level, average_lead_days} | {error},
            "errors": [str] | null,
        }
    """
    mq_result = {}
    mrc_result = {}
    cdf_result = {}
    errors = []

    try:
        mq = get_all_risk_summary()
        mq_result = {
            "total_plans": mq["total_plans"],
            "high_risk_count": mq["high_risk_count"],
            "medium_risk_count": mq["medium_risk_count"],
            "low_risk_count": mq["low_risk_count"],
        }
    except Exception as e:
        errors.append(f"物料风险: {e}")
        mq_result = {"error": f"获取物料风险总览失败: {e}"}

    try:
        mrc = get_all_mrc_summary()
        mrc_result = {
            "total_plans": mrc["total_plans"],
            "average_score": mrc["average_score"],
            "ready_count": mrc["ready_count"],
            "partially_ready_count": mrc["partially_ready_count"],
            "not_ready_count": mrc["not_ready_count"],
        }
    except Exception as e:
        errors.append(f"制造就绪度: {e}")
        mrc_result = {"error": f"获取制造就绪度总览失败: {e}"}

    try:
        cdf = get_cert_dashboard()
        cdf_result = {
            "total_plans": cdf["total_plans"],
            "mandatory_completion_rate": cdf["mandatory_completion_rate"],
            "overall_risk_level": cdf["overall_risk_level"],
            "average_lead_days": cdf["average_lead_days"],
        }
    except Exception as e:
        errors.append(f"认证看板: {e}")
        cdf_result = {"error": f"获取认证看板失败: {e}"}

    return {
        "mq": mq_result,
        "mrc": mrc_result,
        "cdf": cdf_result,
        "errors": errors if errors else None,
    }
