"""冷量联动成本重算引擎

核心功能：
1. 根据产品冷量参数匹配 BTU 段
2. 查询能力段单价计算基准成本
3. 对比实际 BOM 成本生成差异分析
4. 记录重算结果到 CostRecalculationResult

触发方式：
- manual: 用户手动点击"冷量联动重算"
- eco_effective: ECO 生效时自动触发
"""
import logging
import json
import math
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.capacity_unit_cost import CapacityUnitCost
from app.models.cost_recalculation import (
    CostRecalculationResult, CostRecalculationItem,
    RecalcStatus,
)
from app.models.cost_accounting import CostAccountingSheet
from app.models.product_plan import ProductPlan
from app.models.product_plan_subs import ProductPlanInitiation, ProductPlanMarket
from app.models.bom import BOM, BOMItem

logger = logging.getLogger(__name__)

# BTU 段匹配规则（优先级: 精确匹配 → 区间包含 → 最近似）
BTU_SEGMENTS = sorted([
    9000, 12000, 18000, 22000, 24000, 28000, 36000, 48000, 60000
])


def _parse_btu_from_text(text: str) -> Optional[int]:
    """从文本中提取 BTU 数字（支持 '22000'、'22K'、'2.2万'、'18k-24k' 等）
    
    参数来源：产品策划立项数据中的 capacity_range/main_capacity 字段
    返回：匹配的 BTU 数值（取区间平均值），None 表示无法识别
    """
    if not text:
        return None
    
    t = text.strip().upper()
    
    # 尝试直接整数匹配
    # 格式: "22000" 或 "22000BTU"
    import re
    # 区间格式: "18K-24K"、"18000-24000"
    range_match = re.search(r'(\d+)\s*[Kk]?\s*[-~至到]\s*(\d+)\s*[Kk]?', t)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        # 如果有 K 标识，乘以 1000
        if range_match.group(0).upper().count('K') > 0:
            low = low * 1000
            high = high * 1000
        avg = (low + high) // 2
        return _match_btu_segment(avg)
    
    # 单值格式: "22K"、"22000"、"2.2万"
    single_match = re.search(r'(\d+(?:\.\d+)?)\s*(K|万|BTU)?', t)
    if single_match:
        val = float(single_match.group(1))
        unit = single_match.group(2) if single_match.group(2) else ''
        if unit == 'K':
            val = val * 1000
        elif unit == '万':
            val = val * 10000
        return _match_btu_segment(int(val))
    
    return None


def _match_btu_segment(btu: int) -> Optional[int]:
    """将 BTU 值匹配到最近的预定义段
    
    匹配策略：
    - 精确等于 → 返回该段
    - 在两个段之间 → 返回最近的段（取绝对值最小的差值）
    - 超出范围 → 返回最接近的端点
    
    参数来源：容量段在 CapacityUnitCost 中配置
    """
    if not BTU_SEGMENTS:
        return None
    
    # 查数据库中的实际配置段
    # 但 here 我们用预定义段，实际数据生产后会由配置决定
    if btu in BTU_SEGMENTS:
        return btu
    
    # 找最近的
    nearest = min(BTU_SEGMENTS, key=lambda x: abs(x - btu))
    return nearest


def _parse_capacity_key(btu: int) -> str:
    """BTU 值 → 能力段标识，如 22000 → '22K'"""
    if btu >= 1000:
        return f"{btu // 1000}K"
    return str(btu)


def _calc_complexity_factor(product_type: str, series_name: str) -> float:
    """计算产品复杂度系数
    
    基准 = 1.0（常规分体壁挂/柜机）
    复杂机型上浮：
    - 天花/风管/商用 → 1.15
    - 变频/高端系列   → 1.10
    - 热泵            → 1.20
    - 移动空调/窗机   → 0.85（结构更简单）
    
    参数来源：行业经验值，后续可通过数据积累优化
    """
    factor = 1.0
    
    if product_type:
        pt = product_type.lower()
        if any(k in pt for k in ['天花', '风管', '商用', 'ducted', 'cassette', 'ceiling']):
            factor *= 1.15
        elif any(k in pt for k in ['热泵', 'heat pump', 'hp']):
            factor *= 1.20
        elif any(k in pt for k in ['移动', 'portable', '窗机', 'window']):
            factor *= 0.85
        elif any(k in pt for k in ['柜机', 'floor']):
            factor *= 1.05
    
    if series_name:
        sn = series_name.upper()
        # K/L/M 系列为高端/变频
        if sn in ('K', 'L', 'M', 'X'):
            factor *= 1.10
    
    return round(factor, 3)


def _calc_efficiency_score(variance_pct: float) -> float:
    """成本效率评分 0-100
    
    评分规则（经验值）：
    - variance_pct <= 0（实际≤基准）→ 90~100
    - 0 < variance_pct <= 10 → 70~89
    - 10 < variance_pct <= 20 → 50~69
    - 20 < variance_pct <= 30 → 30~49
    - variance_pct > 30 → 0~29
    """
    if variance_pct <= 0:
        return max(90, min(100, 100 + variance_pct))  # 优于基准时加分
    elif variance_pct <= 10:
        return 90 - variance_pct * 2  # 10%→70分
    elif variance_pct <= 20:
        return 70 - (variance_pct - 10) * 2  # 20%→50分
    elif variance_pct <= 30:
        return 50 - (variance_pct - 20) * 2  # 30%→30分
    else:
        return max(0, 30 - (variance_pct - 30) * 2)


def run_capacity_recalculation(
    product_plan_id: str,
    period_id: Optional[int] = None,
    sheet_id: Optional[int] = None,
    trigger_source: str = "manual",
    user_name: Optional[str] = None,
    db: Session = None,
) -> dict:
    """执行冷量联动成本重算 — 核心引擎
    
    参数：
    - product_plan_id: 产品策划ID（必填）
    - period_id: 核算期间ID（可选，用于定位当前核算单）
    - sheet_id: 核算单ID（可选，直接指定）
    - trigger_source: 触发方式
    - user_name: 操作者
    - db: 数据库session
    
    返回：重算结果dict（非数据库持久化视图）
    """
    if not db:
        raise ValueError("db session required")
    
    # 1. 查产品策划
    plan = db.query(ProductPlan).filter(ProductPlan.id == product_plan_id).first()
    if not plan:
        return {"ok": False, "error": "产品策划不存在", "status": "failed"}
    
    # 2. 获取冷量参数
    initiation = db.query(ProductPlanInitiation).filter(
        ProductPlanInitiation.product_plan_id == product_plan_id
    ).first()
    market_info = db.query(ProductPlanMarket).filter(
        ProductPlanMarket.product_plan_id == product_plan_id
    ).first()
    
    # 主销容量优先，其次覆盖容量范围
    capacity_text = None
    if market_info and market_info.main_capacity:
        capacity_text = market_info.main_capacity
    elif initiation and initiation.capacity_range:
        capacity_text = initiation.capacity_range
    
    if not capacity_text:
        # 没有冷量信息 → 跳过
        result = CostRecalculationResult(
            product_plan_id=product_plan_id, period_id=period_id,
            sheet_id=sheet_id, status=RecalcStatus.SKIPPED,
            trigger_source=trigger_source, created_by=user_name,
            remark="产品无冷量参数配置，跳过重算",
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return {"ok": True, "status": "skipped", "id": result.id, "reason": "无冷量参数"}
    
    # 3. 解析 BTU
    btu = _parse_btu_from_text(capacity_text)
    if btu is None:
        result = CostRecalculationResult(
            product_plan_id=product_plan_id, period_id=period_id,
            sheet_id=sheet_id, status=RecalcStatus.FAILED,
            trigger_source=trigger_source, created_by=user_name,
            remark=f"无法解析冷量值: {capacity_text}",
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return {"ok": False, "status": "failed", "id": result.id, "error": f"无法解析冷量: {capacity_text}"}
    
    capacity_key = _parse_capacity_key(btu)
    
    # 4. 查询能力段单价
    cap_cost = db.query(CapacityUnitCost).filter(
        CapacityUnitCost.btu == btu
    ).first()
    if not cap_cost:
        # 尝试匹配最接近的 BTU 段
        all_caps = db.query(CapacityUnitCost).order_by(CapacityUnitCost.btu).all()
        if all_caps:
            nearest = min(all_caps, key=lambda c: abs(c.btu - btu))
            cap_cost = nearest
            matched_btu = nearest.btu
            capacity_key = _parse_capacity_key(nearest.btu)
        else:
            # 无任何配置 → 跳过
            result = CostRecalculationResult(
                product_plan_id=product_plan_id, period_id=period_id,
                sheet_id=sheet_id, status=RecalcStatus.SKIPPED,
                trigger_source=trigger_source, created_by=user_name,
                remark="冷量段单价未配置，请先配置 CapacityUnitCost",
            )
            db.add(result)
            db.commit()
            db.refresh(result)
            return {"ok": True, "status": "skipped", "id": result.id, "reason": "冷量段单价未配置"}
    else:
        matched_btu = btu
    
    # 5. 计算复杂度系数
    product_type = initiation.product_type if initiation else None
    series_name = plan.series
    complexity = _calc_complexity_factor(product_type or "", series_name or "")
    
    # 6. 基准成本 = 能力段单价(万元) × 10000 → 元 × 复杂度系数
    unit_cost_w = float(cap_cost.unit_cost_w or 0)
    baseline_material = round(unit_cost_w * 10000 * complexity, 2)
    
    # 7. 获取实际 BOM 成本
    actual_bom_cost = 0.0
    bom_id = None
    bom_no = None
    
    # 通过核算单中的链路获取 BOM
    sheet = None
    if sheet_id:
        sheet = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sheet_id).first()
    elif period_id:
        sheet = db.query(CostAccountingSheet).filter(
            CostAccountingSheet.product_plan_id == product_plan_id,
            CostAccountingSheet.period_id == period_id,
        ).order_by(desc(CostAccountingSheet.created_at)).first()
    
    if sheet:
        bom_id = None
        # 从 plan 链路找 BOM
        if plan.project_links:
            primary = None
            for link in plan.project_links:
                if link.link_type == 'primary':
                    primary = link.project_id
                    break
            if primary:
                from app.models.project import Project
                project = db.query(Project).filter(Project.id == primary).first()
                if project and project.product_code:
                    bom = db.query(BOM).filter(
                        BOM.product_code == project.product_code,
                        BOM.status == "released",
                    ).order_by(desc(BOM.created_at)).first()
                    if bom:
                        bom_id = bom.id
                        bom_no = bom.bom_no
                        actual_bom_cost = sheet.material_cost_actual
        # 如果没找到 BOM，用 sheet 中的物料成本
        if not bom_id and sheet.material_cost_actual > 0:
            actual_bom_cost = sheet.material_cost_actual
    
    # 8. 计算差异
    variance = round(actual_bom_cost - baseline_material, 2)
    variance_pct = round(variance / baseline_material * 100, 2) if baseline_material > 0 else 0
    efficiency = _calc_efficiency_score(variance_pct)
    
    # 9. 创建重算结果
    result = CostRecalculationResult(
        product_plan_id=product_plan_id, period_id=period_id,
        sheet_id=sheet_id,
        main_capacity=capacity_text, matched_btu=matched_btu,
        capacity_key=capacity_key,
        baseline_material_cost=baseline_material,
        complexity_factor=complexity,
        actual_bom_cost=actual_bom_cost,
        bom_id=bom_id, bom_no=bom_no,
        variance_amount=variance, variance_pct=variance_pct,
        cost_efficiency_score=round(efficiency, 1),
        status=RecalcStatus.COMPLETED,
        trigger_source=trigger_source, created_by=user_name,
    )
    db.add(result)
    db.flush()  # 获取 ID
    
    # 10. 创建明细行
    items = []
    items.append(CostRecalculationItem(
        result_id=result.id, dimension="material",
        item_name="冷量基准成本",
        baseline_amount=baseline_material, actual_amount=actual_bom_cost,
        variance=variance, variance_pct=variance_pct,
        remark=f"BTU={matched_btu}, 段单价={unit_cost_w}万元, 复杂度={complexity}",
    ))
    
    # 从核算单获取人工和费用数据
    if sheet:
        items.append(CostRecalculationItem(
            result_id=result.id, dimension="labor",
            item_name="人工成本",
            baseline_amount=0, actual_amount=sheet.labor_cost_actual,
            variance=sheet.labor_cost_actual, variance_pct=100 if sheet.labor_cost_actual > 0 else 0,
            remark="人工成本尚无冷量基准（待扩展）",
        ))
        items.append(CostRecalculationItem(
            result_id=result.id, dimension="overhead",
            item_name="制造费用",
            baseline_amount=0, actual_amount=sheet.overhead_cost_actual,
            variance=sheet.overhead_cost_actual, variance_pct=100 if sheet.overhead_cost_actual > 0 else 0,
            remark="制造费用尚无冷量基准（待扩展）",
        ))
    
    for item in items:
        db.add(item)
    
    db.commit()
    db.refresh(result)
    
    return {
        "ok": True,
        "status": "completed",
        "id": result.id,
        "data": {
            "product_plan_id": product_plan_id,
            "main_capacity": capacity_text,
            "matched_btu": matched_btu,
            "capacity_key": capacity_key,
            "unit_cost_w": unit_cost_w,
            "complexity_factor": complexity,
            "baseline_material_cost": baseline_material,
            "actual_bom_cost": actual_bom_cost,
            "variance_amount": variance,
            "variance_pct": variance_pct,
            "cost_efficiency_score": round(efficiency, 1),
            "items": [
                {"dimension": i.dimension, "item_name": i.item_name,
                 "baseline": i.baseline_amount, "actual": i.actual_amount,
                 "variance": i.variance, "variance_pct": i.variance_pct,
                 "remark": i.remark}
                for i in items
            ],
        },
    }
