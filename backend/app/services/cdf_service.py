"""CDF Service — 认证决策引擎 (Phase 4: Intelligence Layer)

评估产品需要哪些认证、认证风险及建议路线。

认证类型:
- CCC: 中国强制认证
- CE: 欧盟安全认证
- UL: 美国安全认证
- ETL: 美国(Intertek)
- RoHS: 有害物质限制
- REACH: 化学品注册(欧盟)
- ERP: 能效相关产品(欧盟)
- CB: 国际通用

联动场景:
  PLAN_RELEASED → 自动评估认证需求
  如果目标市场有认证缺失 → 预警：缺少必要认证
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── 各国/地区认证要求 ──
MARKET_CERTIFICATIONS = {
    "中国": [{"code": "CCC", "name": "中国强制认证", "mandatory": True, "lead_time_days": 60}],
    "欧盟": [
        {"code": "CE", "name": "CE安全认证", "mandatory": True, "lead_time_days": 30},
        {"code": "RoHS", "name": "RoHS有害物质", "mandatory": True, "lead_time_days": 15},
        {"code": "REACH", "name": "REACH化学品注册", "mandatory": True, "lead_time_days": 30},
        {"code": "ERP", "name": "能效认证", "mandatory": True, "lead_time_days": 45},
    ],
    "美国": [
        {"code": "UL", "name": "UL安全认证", "mandatory": False, "lead_time_days": 90},
        {"code": "ETL", "name": "ETL认证", "mandatory": False, "lead_time_days": 60},
        {"code": "RoHS", "name": "RoHS有害物质", "mandatory": True, "lead_time_days": 15},
        {"code": "ENERGY_STAR", "name": "能源之星", "mandatory": False, "lead_time_days": 45},
    ],
    "东南亚": [
        {"code": "CB", "name": "CB国际认证", "mandatory": True, "lead_time_days": 45},
    ],
    "中东": [
        {"code": "CB", "name": "CB国际认证", "mandatory": True, "lead_time_days": 45},
        {"code": "RoHS", "name": "RoHS有害物质", "mandatory": True, "lead_time_days": 15},
    ],
}


def assess_certification_requirements(plan_id: str,
                                       target_markets: Optional[List[str]] = None,
                                       product_type: str = "空调") -> dict:
    """评估认证需求

    Args:
        plan_id: ProductPlan ID
        target_markets: 目标市场列表（如 ["中国", "欧盟"]）
        product_type: 产品类型

    Returns:
        {
            "plan_id": str,
            "product_type": str,
            "required_certs": [{code, name, mandatory, lead_time_days}],
            "estimated_lead_days": int (最长认证周期),
            "risk_level": "low|medium|high",
            "recommendation": str,
        }
    """
    try:
        markets = target_markets or _fetch_target_markets(plan_id)
        if not markets:
            return {
                "plan_id": plan_id,
                "product_type": product_type,
                "required_certs": [],
                "estimated_lead_days": 0,
                "risk_level": "low",
                "recommendation": "无目标市场，暂无需认证评估",
            }

        required_certs = []
        for market in markets:
            certs = MARKET_CERTIFICATIONS.get(market, [])
            for cert in certs:
                if cert not in required_certs:
                    required_certs.append(cert)

        # 最长认证周期
        max_lead = max(c["lead_time_days"] for c in required_certs) if required_certs else 0

        # 风险评估
        mandatory_count = sum(1 for c in required_certs if c["mandatory"])
        high_risk_certs = [c for c in required_certs if c["lead_time_days"] > 60]

        if mandatory_count >= 4 or len(high_risk_certs) >= 2:
            risk_level = "high"
            recommendation = f"需 {mandatory_count} 项强制认证({max_lead}天)，建议立即启动认证流程"
        elif mandatory_count >= 2:
            risk_level = "medium"
            recommendation = f"需 {mandatory_count} 项强制认证({max_lead}天)，认证风险可控"
        else:
            risk_level = "low"
            recommendation = f"认证需求简单，{max_lead}天可完成"

        return {
            "plan_id": plan_id,
            "product_type": product_type,
            "target_markets": markets,
            "required_certs": required_certs,
            "estimated_lead_days": max_lead,
            "risk_level": risk_level,
            "recommendation": recommendation,
        }

    except Exception as e:
        logger.exception("认证评估失败: plan=%s", plan_id)
        return {"plan_id": plan_id, "error": str(e), "risk_level": "high"}


def _fetch_target_markets(plan_id: str) -> List[str]:
    """从数据库获取目标市场"""
    db = None
    try:
        from app.core.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        row = db.execute(
            text("SELECT target_markets FROM product_plans WHERE id = :plan_id"),
            {"plan_id": plan_id},
        ).fetchone()
        if row and row[0]:
            raw = row[0]
            if isinstance(raw, str):
                import json
                return json.loads(raw) if raw.startswith("[") else [raw]
            return list(raw) if isinstance(raw, (list, tuple)) else []
        return ["中国"]
    except Exception:
        return ["中国"]  # 默认中国市场
    finally:
        if db:
            db.close()


def get_certification_timeline(required_certs: List[dict]) -> List[dict]:
    """生成认证时间线（按紧急程度排序）

    强制认证优先，短周期认证可并行。
    """
    mandatory = [c for c in required_certs if c["mandatory"]]
    optional = [c for c in required_certs if not c["mandatory"]]

    timeline = []
    phase = 1
    for cert in sorted(mandatory, key=lambda x: x["lead_time_days"]):
        timeline.append({
            "phase": phase,
            "code": cert["code"],
            "name": cert["name"],
            "lead_days": cert["lead_time_days"],
            "type": "mandatory",
            "can_parallel": True,
        })
        phase += 1

    for cert in optional:
        timeline.append({
            "phase": phase,
            "code": cert["code"],
            "name": cert["name"],
            "lead_days": cert["lead_time_days"],
            "type": "optional",
            "can_parallel": True,
        })
        phase += 1

    return timeline


# ═══════════════════════════════════════════
# 仪表盘聚合方法（不破坏现有 assess_certification_requirements）
# ═══════════════════════════════════════════


def _fetch_all_plan_ids() -> List[str]:
    """从 product_plans 表获取所有 plan_id"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT id FROM product_plans ORDER BY created_at DESC")
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        logger.warning("查询 product_plans 失败，返回空列表")
        return []
    finally:
        db.close()


def get_cert_dashboard() -> dict:
    """认证看板 — 各类型认证进度和强制认证完成率汇总

    遍历所有计划，聚合每项认证的覆盖情况和完成状态。

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
    plan_ids = _fetch_all_plan_ids()
    total = len(plan_ids)

    # 认证统计: {code: {name, mandatory, required_plans: set}}
    cert_stats: Dict[str, dict] = {}
    total_lead = 0
    risk_scores = []
    low_risk_plans: set = set()  # 追踪低风险的 plan

    for pid in plan_ids:
        result = assess_certification_requirements(pid)
        certs = result.get("required_certs", [])
        total_lead += result.get("estimated_lead_days", 0)

        # 风险评分映射
        rl = result.get("risk_level", "low")
        risk_scores.append({"high": 3, "medium": 2, "low": 1}.get(rl, 1))
        if rl == "low":
            low_risk_plans.add(pid)

        for cert in certs:
            code = cert["code"]
            if code not in cert_stats:
                cert_stats[code] = {
                    "code": code,
                    "name": cert["name"],
                    "mandatory": cert.get("mandatory", False),
                    "lead_time_days": cert.get("lead_time_days", 0),
                    "required_plans": set(),
                    "completed_plans": set(),  # TODO: 对接认证完成状态表
                }
            cert_stats[code]["required_plans"].add(pid)

    # 简单填充逻辑: 假设所有风险等级为 low 的 plan 已完成认证 (占位, 后续接入真实数据)
    for stats in cert_stats.values():
        stats["completed_plans"] = {pid for pid in stats["required_plans"] if pid in low_risk_plans}

    # 构建结果
    cert_type_summary = []
    mandatory_total = 0
    mandatory_completed = 0

    for code, stats in cert_stats.items():
        req_count = len(stats["required_plans"])
        comp_count = len(stats["completed_plans"])
        rate = round(comp_count / req_count * 100, 1) if req_count else 0

        cert_type_summary.append({
            "code": stats["code"],
            "name": stats["name"],
            "mandatory": stats["mandatory"],
            "lead_time_days": stats["lead_time_days"],
            "required_plans_count": req_count,
            "completed_count": comp_count,
            "completion_rate": rate,
        })

        if stats["mandatory"]:
            mandatory_total += req_count
            mandatory_completed += comp_count

    overall_mandatory_rate = round(mandatory_completed / mandatory_total * 100, 1) if mandatory_total else 100.0
    avg_lead = round(total_lead / total, 1) if total else 0
    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 1
    if avg_risk >= 2.5:
        overall_risk = "high"
    elif avg_risk >= 1.5:
        overall_risk = "medium"
    else:
        overall_risk = "low"

    return {
        "total_plans": total,
        "cert_type_summary": cert_type_summary,
        "mandatory_completion_rate": overall_mandatory_rate,
        "overall_risk_level": overall_risk,
        "average_lead_days": avg_lead,
    }


def get_plan_cert_detail(plan_id: str) -> dict:
    """单个计划的认证要求 + 时间线详情

    综合 assess_certification_requirements 和 get_certification_timeline，
    返回完整的认证需求、风险评估和推进时间线。

    Args:
        plan_id: ProductPlan ID

    Returns:
        {
            "plan_id": str,
            "product_type": str,
            "target_markets": [str],
            "required_certs": [{code, name, mandatory, lead_time_days}],
            "estimated_lead_days": int,
            "risk_level": str,
            "recommendation": str,
            "timeline": [{phase, code, name, lead_days, type, can_parallel}],
        }
    """
    result = assess_certification_requirements(plan_id)
    certs = result.get("required_certs", [])
    timeline = get_certification_timeline(certs)
    result["timeline"] = timeline
    return result
