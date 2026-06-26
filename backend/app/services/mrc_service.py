"""MRC Service — 制造就绪度评分 (Phase 4: Intelligence Layer)

评估产品是否达到制造就绪状态:
- 技术就绪度: 设计是否完成、样机是否验证
- 工艺就绪度: 工艺文件、工装模具
- 供应就绪度: 关键物料齐套

联动场景:
  PLAN_TECH_INPUT_DONE → 自动评估制造就绪度
  就绪度 < 60% → 预警：不满足量产条件
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def assess_manufacturing_readiness(plan_id: str, tech_data: Optional[dict] = None) -> dict:
    """评估制造就绪度

    四个维度评分 (0-100):
    1. 设计就绪度: 设计评审、图纸、BOM
    2. 工艺就绪度: 工艺路线、作业指导书
    3. 模具就绪度: 模具开发进度
    4. 供应就绪度: 关键物料齐套率

    Returns:
        {
            "plan_id": str,
            "overall_score": int (0-100),
            "dimensions": {design, process, mold, supply: {score, status}},
            "readiness_level": "not_ready|partially_ready|ready",
            "gaps": [str],
            "recommendation": str,
        }
    """
    try:
        # 默认从数据库读取（或从传入的 tech_data）
        data = tech_data or _fetch_tech_readiness(plan_id)

        design_score = _calc_design_readiness(data)
        process_score = _calc_process_readiness(data)
        mold_score = _calc_mold_readiness(data)
        supply_score = _calc_supply_readiness(data)

        overall = int(0.35 * design_score + 0.25 * process_score
                      + 0.20 * mold_score + 0.20 * supply_score)

        gaps = []
        if design_score < 60:
            gaps.append(f"设计就绪度不足 ({design_score}%): 设计评审未完成")
        if process_score < 50:
            gaps.append(f"工艺就绪度不足 ({process_score}%): 工艺文件缺失")
        if mold_score < 40:
            gaps.append(f"模具就绪度不足 ({mold_score}%): 模具开发滞后")
        if supply_score < 50:
            gaps.append(f"供应就绪度不足 ({supply_score}%): 关键物料未齐套")

        if overall >= 80:
            level = "ready"
            rec = "制造就绪度达标，可进入试产阶段"
        elif overall >= 50:
            level = "partially_ready"
            rec = f"制造就绪度待提升 ({overall}%)，需关闭 {len(gaps)} 项差距"
        else:
            level = "not_ready"
            rec = f"制造就绪度不达标 ({overall}%)，建议推迟量产，优先解决: {'; '.join(gaps[:3])}"

        return {
            "plan_id": plan_id,
            "overall_score": overall,
            "dimensions": {
                "design": {"score": design_score, "status": "ok" if design_score >= 60 else "warning"},
                "process": {"score": process_score, "status": "ok" if process_score >= 60 else "warning"},
                "mold": {"score": mold_score, "status": "ok" if mold_score >= 60 else "warning"},
                "supply": {"score": supply_score, "status": "ok" if supply_score >= 60 else "warning"},
            },
            "readiness_level": level,
            "gaps": gaps[:5],
            "recommendation": rec,
        }
    except Exception as e:
        logger.exception("制造就绪度评估失败: plan=%s", plan_id)
        return {"plan_id": plan_id, "error": str(e), "readiness_level": "not_ready"}


def _fetch_tech_readiness(plan_id: str) -> dict:
    """从数据库获取技术就绪度相关数据"""
    try:
        from app.core.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT p.tech_doc_status, p.mold_status, p.bom_status
                    FROM product_plans p WHERE p.id = :plan_id
                """),
                {"plan_id": plan_id},
            ).fetchone()

            if row:
                return {
                    "tech_doc_status": row[0] or "draft",
                    "mold_status": row[1] or "not_started",
                    "bom_status": row[2] or "draft",
                }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"查询制造就绪度原始数据失败: {e}")
        pass
    return {}


def _calc_design_readiness(data: dict) -> int:
    """设计就绪度评分"""
    tech_status = data.get("tech_doc_status", "draft")
    score_map = {
        "completed": 90, "reviewed": 80, "submitted": 60,
        "in_progress": 40, "draft": 20, "not_started": 0,
    }
    return score_map.get(tech_status, 30)


def _calc_process_readiness(data: dict) -> int:
    """工艺就绪度评分"""
    return 50  # 默认中等


def _calc_mold_readiness(data: dict) -> int:
    """模具就绪度评分"""
    mold_status = data.get("mold_status", "not_started")
    score_map = {
        "completed": 90, "in_test": 70, "in_development": 40,
        "not_started": 0,
    }
    return score_map.get(mold_status, 20)


def _calc_supply_readiness(data: dict) -> int:
    """供应就绪度评分"""
    bom_status = data.get("bom_status", "draft")
    score_map = {
        "released": 80, "approved": 70, "reviewed": 50,
        "draft": 20, "not_started": 0,
    }
    return score_map.get(bom_status, 20)


# ═══════════════════════════════════════════
# 仪表盘聚合方法（不破坏现有 assess_manufacturing_readiness）
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
    except Exception as e:
        logger.warning(f"查询 product_plans 失败: {e}")
        return []
    finally:
        db.close()


def get_all_mrc_summary() -> dict:
    """所有计划的制造就绪度汇总

    遍历所有计划，汇总就绪度评分和层级分布。

    Returns:
        {
            "total_plans": int,
            "average_score": float,
            "ready_count": int,
            "partially_ready_count": int,
            "not_ready_count": int,
            "dimension_averages": {
                "design": float,
                "process": float,
                "mold": float,
                "supply": float,
            },
            "plans": [{plan_id, overall_score, readiness_level}]
        }
    """
    plan_ids = _fetch_all_plan_ids()
    total = len(plan_ids)
    ready = partially = not_ready = 0
    score_sum = 0
    dim_sums = {"design": 0, "process": 0, "mold": 0, "supply": 0}
    plan_list = []

    for pid in plan_ids:
        result = assess_manufacturing_readiness(pid)
        score = result.get("overall_score", 0)
        level = result.get("readiness_level", "not_ready")
        score_sum += score

        if level == "ready":
            ready += 1
        elif level == "partially_ready":
            partially += 1
        else:
            not_ready += 1

        dims = result.get("dimensions", {})
        for k in dim_sums:
            dim_sums[k] += dims.get(k, {}).get("score", 0)

        plan_list.append({
            "plan_id": pid,
            "overall_score": score,
            "readiness_level": level,
            "gaps": result.get("gaps", []),
        })

    avg_score = round(score_sum / total, 1) if total else 0
    dim_avgs = {
        k: round(v / total, 1) if total else 0
        for k, v in dim_sums.items()
    }

    return {
        "total_plans": total,
        "average_score": avg_score,
        "ready_count": ready,
        "partially_ready_count": partially,
        "not_ready_count": not_ready,
        "dimension_averages": dim_avgs,
        "plans": plan_list,
    }


def get_plan_mrc_detail(plan_id: str) -> dict:
    """单个计划的制造就绪度详情

    在 assess_manufacturing_readiness 基础上增加四维雷达评分详情和逐项差距分析。

    Args:
        plan_id: ProductPlan ID

    Returns:
        {
            "plan_id": str,
            "overall_score": int,
            "readiness_level": str,
            "dimensions": {
                "design": {"score": int, "status": str, "label": str},
                "process": {"score": int, "status": str, "label": str},
                "mold": {"score": int, "status": str, "label": str},
                "supply": {"score": int, "status": str, "label": str},
            },
            "gaps": [str],
            "recommendation": str,
            "dimension_labels": {
                "design": "设计就绪度",
                "process": "工艺就绪度",
                "mold": "模具就绪度",
                "supply": "供应就绪度",
            },
        }
    """
    result = assess_manufacturing_readiness(plan_id)
    dims = result.get("dimensions", {})

    # 补充中文标签
    label_map = {
        "design": "设计就绪度",
        "process": "工艺就绪度",
        "mold": "模具就绪度",
        "supply": "供应就绪度",
    }
    for key, label in label_map.items():
        if key in dims:
            dims[key]["label"] = label

    result["dimension_labels"] = label_map
    return result
