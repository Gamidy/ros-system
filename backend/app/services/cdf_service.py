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
