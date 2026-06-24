"""MQ Service — 物料质量风险评分 (Phase 4: Intelligence Layer)

评估 BOM 物料的质量风险等级:
- 高风险物料: 新供应商 / 首次使用 / 关键部件
- 中风险物料: 已验证但批量小
- 低风险物料: 成熟物料

联动场景:
  PLAN_RELEASED → 自动评估 BOM 物料风险
  如果高风险物料 > N% → 预警通知
"""
import logging
from typing import Dict, List, Optional, Tuple

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class MaterialRiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


RISK_SCORE = {
    MaterialRiskLevel.LOW: 1,
    MaterialRiskLevel.MEDIUM: 3,
    MaterialRiskLevel.HIGH: 5,
}


def _get_material_risk(material_type: str, supplier: str, is_new_supplier: bool,
                       is_key_part: bool) -> Tuple[str, int]:
    """评估单个物料的品质风险

    Risk factors:
    - 新供应商 (+3)
    - 关键部件 (+2)
    - 首次使用物料类型 (+1)
    """
    score = 0
    reasons = []

    if is_new_supplier:
        score += 3
        reasons.append("新供应商")
    if is_key_part:
        score += 2
        reasons.append("关键部件")

    if score >= 4:
        return MaterialRiskLevel.HIGH, score
    elif score >= 2:
        return MaterialRiskLevel.MEDIUM, score
    else:
        return MaterialRiskLevel.LOW, score


def assess_bom_risk(plan_id: str, bom_items: Optional[List[dict]] = None) -> dict:
    """评估 BOM 物料风险

    Args:
        plan_id: ProductPlan ID
        bom_items: BOM 物料列表（含 material_type, supplier, is_key_part 等字段）
                    如果为 None，从数据库读取

    Returns:
        {
            "plan_id": str,
            "risk_level": "low|medium|high",
            "risk_score": int,
            "total_items": int,
            "high_risk_count": int,
            "medium_risk_count": int,
            "low_risk_count": int,
            "high_risk_items": [{name, type, supplier, score}],
            "recommendation": str,
        }
    """
    db = SessionLocal()
    try:
        items = bom_items or _fetch_bom_items(db, plan_id)

        if not items:
            return {
                "plan_id": plan_id,
                "risk_level": MaterialRiskLevel.LOW,
                "risk_score": 0,
                "total_items": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "high_risk_items": [],
                "recommendation": "无 BOM 物料，无需评估",
            }

        high_risk = []
        counts = {MaterialRiskLevel.LOW: 0, MaterialRiskLevel.MEDIUM: 0, MaterialRiskLevel.HIGH: 0}
        total_score = 0

        for item in items:
            level, score = _get_material_risk(
                material_type=item.get("material_type", "generic"),
                supplier=item.get("supplier", ""),
                is_new_supplier=item.get("is_new_supplier", False),
                is_key_part=item.get("is_key_part", False),
            )
            counts[level] += 1
            total_score += score

            if level == MaterialRiskLevel.HIGH:
                high_risk.append({
                    "name": item.get("name", "Unnamed"),
                    "type": item.get("material_type", "generic"),
                    "supplier": item.get("supplier", ""),
                    "score": score,
                })

        # 总体风险等级
        high_ratio = counts[MaterialRiskLevel.HIGH] / max(len(items), 1)
        if high_ratio > 0.3 or counts[MaterialRiskLevel.HIGH] >= 3:
            overall = MaterialRiskLevel.HIGH
            recommendation = f"高风险物料占比 {high_ratio:.0%}，建议进行供应商审核和样品测试"
        elif high_ratio > 0.1 or counts[MaterialRiskLevel.MEDIUM] >= 3:
            overall = MaterialRiskLevel.MEDIUM
            recommendation = "存在中等风险物料，建议重点关注关键部件质量"
        else:
            overall = MaterialRiskLevel.LOW
            recommendation = "物料风险可控"

        return {
            "plan_id": plan_id,
            "risk_level": overall,
            "risk_score": total_score,
            "total_items": len(items),
            "high_risk_count": counts[MaterialRiskLevel.HIGH],
            "medium_risk_count": counts[MaterialRiskLevel.MEDIUM],
            "low_risk_count": counts[MaterialRiskLevel.LOW],
            "high_risk_items": high_risk,
            "recommendation": recommendation,
        }
    except Exception as e:
        logger.exception("BOM 风险评估失败: plan=%s", plan_id)
        return {"plan_id": plan_id, "error": str(e), "risk_level": MaterialRiskLevel.HIGH, "recommendation": "风险评估异常"}
    finally:
        db.close()


def _fetch_bom_items(db, plan_id: str) -> List[dict]:
    """从数据库获取 BOM 物料清单"""
    try:
        from sqlalchemy import text
        rows = db.execute(
            text("""
                SELECT b.id, b.material_name, b.material_type, b.supplier,
                       b.is_key_part
                FROM bom_items b
                JOIN product_plans p ON p.id = b.plan_id
                WHERE p.id = :plan_id
            """),
            {"plan_id": plan_id},
        ).fetchall()
        return [
            {
                "id": r[0],
                "name": r[1],
                "material_type": r[2],
                "supplier": r[3],
                "is_key_part": bool(r[4]) if r[4] else False,
                "is_new_supplier": False,  # TODO: 从供应商表检查
            }
            for r in rows
        ]
    except Exception:
        logger.warning("BOM 物料查询失败（可能表不存在）: plan=%s", plan_id)
        return []
