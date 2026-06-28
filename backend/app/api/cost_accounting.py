"""成本核算系统 — 期间/费率/分摊/核算单CRUD"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, text
import random, string

from app.core.database import get_db
from app.core.security import get_current_user, require_role, require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan
from app.models.cost_accounting import (
    CostAccountingPeriod, CostAccountingSheet, CostAccountingItem,
    LaborRateConfig, ProductLaborCost,
    OverheadAllocationRule, ProductOverheadCost,
    PeriodStatus, SheetStatus, CostCategory, AllocationBase,
)
from app.models.indirect_cost_config import IndirectCostConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cost-accounting", tags=["cost-accounting"])

_PERIOD_DEP = Depends(require_menu("cost-accounting"))

# ═══════════
# Schemas
# ═══════════

class PeriodCreate(BaseModel):
    period_name: str
    start_date: str
    end_date: str

class PeriodOut(BaseModel):
    id: int; period_name: str; start_date: str; end_date: str
    status: str; org_id: Optional[int] = None
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class LaborRateCreate(BaseModel):
    operation_code: str; operation_name: str; hourly_rate: float

class LaborRateOut(BaseModel):
    id: int; operation_code: str; operation_name: str
    hourly_rate: float; unit: str; status: str; org_id: Optional[int] = None
    class Config: from_attributes = True

class LaborCostCreate(BaseModel):
    operation_code: str; operation_name: str; labor_hours: float; hourly_rate: float

class LaborCostOut(BaseModel):
    id: int; product_plan_id: str; period_id: int; operation_code: str
    operation_name: str; labor_hours: float; hourly_rate: float
    total_amount: float; org_id: Optional[int] = None
    class Config: from_attributes = True

class OverheadRuleCreate(BaseModel):
    rule_name: str; allocation_base: str; allocation_rate: float
    description: Optional[str] = None; priority: int = 0

class OverheadRuleOut(BaseModel):
    id: int; rule_name: str; description: Optional[str] = None
    allocation_base: str; allocation_rate: float
    is_active: int; priority: int; org_id: Optional[int] = None
    class Config: from_attributes = True

class OverheadCostOut(BaseModel):
    id: int; product_plan_id: str; period_id: int; rule_id: int
    base_amount: float; allocation_rate: float; allocation_amount: float
    class Config: from_attributes = True

class SheetItemOut(BaseModel):
    id: int; cost_category: str; item_name: str
    target_amount: float; actual_amount: float
    variance: float; variance_pct: float
    source_type: Optional[str] = None
    class Config: from_attributes = True

class SheetOut(BaseModel):
    id: int; sheet_no: str; product_plan_id: str; period_id: int
    status: str
    material_cost_actual: float; material_cost_target: float
    labor_cost_actual: float; labor_cost_target: float
    overhead_cost_actual: float; overhead_cost_target: float
    total_cost_actual: float; total_cost_target: float
    variance_amount: float; variance_pct: float
    currency: str; created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    items: List[SheetItemOut] = []
    class Config: from_attributes = True

class VarianceOut(BaseModel):
    material_variance: float; material_variance_pct: float
    labor_variance: float; labor_variance_pct: float
    overhead_variance: float; overhead_variance_pct: float
    total_variance: float; total_variance_pct: float

# ═══════════
# 核算期间管理
# ═══════════

@router.get("/periods", response_model=List[PeriodOut])
def list_periods(db: Session = Depends(get_db), _=_PERIOD_DEP) -> List[PeriodOut]:
    return db.query(CostAccountingPeriod).order_by(desc(CostAccountingPeriod.start_date)).all()

@router.post("/periods", response_model=PeriodOut)
def create_period(data: PeriodCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> PeriodOut:
    p = CostAccountingPeriod(period_name=data.period_name, start_date=data.start_date, end_date=data.end_date)
    db.add(p); db.commit(); db.refresh(p); return p

@router.patch("/periods/{pid}", response_model=PeriodOut)
def update_period(pid: int, data: PeriodCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> PeriodOut:
    p = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == pid).first()
    if not p: raise HTTPException(404, "期间不存在")
    if p.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "已关闭期间不可修改")
    p.period_name = data.period_name; p.start_date = data.start_date; p.end_date = data.end_date
    db.commit(); db.refresh(p); return p

@router.delete("/periods/{pid}")
def delete_period(pid: int, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    p = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == pid).first()
    if not p: raise HTTPException(404, "期间不存在")
    if p.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "已关闭期间不可删除")
    db.delete(p); db.commit(); return {"ok": True}

@router.post("/periods/{pid}/close", response_model=PeriodOut)
def close_period(pid: int, db: Session = Depends(get_db), _=_PERIOD_DEP) -> PeriodOut:
    p = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == pid).first()
    if not p: raise HTTPException(404, "期间不存在")
    if p.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "期间已关闭")
    p.status = PeriodStatus.CLOSED.value; db.commit(); db.refresh(p); return p

# ═══════════
# 工时费率配置
# ═══════════

@router.get("/labor-rates", response_model=List[LaborRateOut])
def list_labor_rates(db: Session = Depends(get_db), _=_PERIOD_DEP) -> list:
    return db.query(LaborRateConfig).order_by(LaborRateConfig.operation_code).all()

@router.post("/labor-rates", response_model=LaborRateOut)
def create_labor_rate(data: LaborRateCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = LaborRateConfig(operation_code=data.operation_code, operation_name=data.operation_name, hourly_rate=data.hourly_rate)
    db.add(r); db.commit(); db.refresh(r); return r

@router.patch("/labor-rates/{rid}")
def update_labor_rate(rid: int, data: LaborRateCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(LaborRateConfig).filter(LaborRateConfig.id == rid).first()
    if not r: raise HTTPException(404, "费率不存在")
    for k, v in data.dict().items(): setattr(r, k, v)
    db.commit(); return {"ok": True}

@router.delete("/labor-rates/{rid}")
def delete_labor_rate(rid: int, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(LaborRateConfig).filter(LaborRateConfig.id == rid).first()
    if not r: raise HTTPException(404, "费率不存在")
    db.delete(r); db.commit(); return {"ok": True}

# ═══════════
# 产品人工成本
# ═══════════

@router.get("/product/{plan_id}/labor-costs", response_model=List[LaborCostOut])
def list_product_labor(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP) -> list:
    q = db.query(ProductLaborCost).filter(
        ProductLaborCost.product_plan_id == plan_id,
        ProductLaborCost.period_id == period_id,
    ).order_by(ProductLaborCost.operation_code).all()
    return q

@router.post("/product/{plan_id}/labor-costs", response_model=LaborCostOut)
def create_product_labor(plan_id: str, period_id: int = Query(...), data: LaborCostCreate = Body(...), db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = ProductLaborCost(
        product_plan_id=plan_id, period_id=period_id,
        operation_code=data.operation_code, operation_name=data.operation_name,
        labor_hours=data.labor_hours, hourly_rate=data.hourly_rate,
        total_amount=round(data.labor_hours * data.hourly_rate, 2),
    )
    db.add(r); db.commit(); db.refresh(r); return r

@router.patch("/product/{plan_id}/labor-costs/{lid}")
def update_product_labor(lid: int, data: LaborCostCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(ProductLaborCost).filter(ProductLaborCost.id == lid).first()
    if not r: raise HTTPException(404, "记录不存在")
    r.labor_hours = data.labor_hours; r.hourly_rate = data.hourly_rate
    r.operation_code = data.operation_code; r.operation_name = data.operation_name
    r.total_amount = round(data.labor_hours * data.hourly_rate, 2)
    db.commit(); return {"ok": True}

@router.delete("/product/{plan_id}/labor-costs/{lid}")
def delete_product_labor(lid: int, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(ProductLaborCost).filter(ProductLaborCost.id == lid).first()
    if not r: raise HTTPException(404, "记录不存在")
    db.delete(r); db.commit(); return {"ok": True}

@router.post("/product/{plan_id}/calculate-labor")
def calculate_labor(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    """按最新费率重新计算产品人工成本"""
    records = db.query(ProductLaborCost).filter(
        ProductLaborCost.product_plan_id == plan_id,
        ProductLaborCost.period_id == period_id,
    ).all()
    updated = 0
    for r in records:
        config = db.query(LaborRateConfig).filter(LaborRateConfig.operation_code == r.operation_code).first()
        if config:
            r.hourly_rate = config.hourly_rate
            r.total_amount = round(r.labor_hours * config.hourly_rate, 2)
            updated += 1
    db.commit()
    return {"ok": True, "updated": updated}

# ═══════════
# 间接费分摊规则
# ═══════════

@router.get("/overhead-rules", response_model=List[OverheadRuleOut])
def list_overhead_rules(db: Session = Depends(get_db), _=_PERIOD_DEP) -> list:
    return db.query(OverheadAllocationRule).order_by(OverheadAllocationRule.priority).all()

@router.post("/overhead-rules", response_model=OverheadRuleOut)
def create_overhead_rule(data: OverheadRuleCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = OverheadAllocationRule(
        rule_name=data.rule_name, allocation_base=data.allocation_base,
        allocation_rate=data.allocation_rate, description=data.description,
        priority=data.priority,
    )
    db.add(r); db.commit(); db.refresh(r); return r

@router.patch("/overhead-rules/{rid}")
def update_overhead_rule(rid: int, data: OverheadRuleCreate, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == rid).first()
    if not r: raise HTTPException(404, "规则不存在")
    for k, v in data.dict().items(): setattr(r, k, v)
    db.commit(); return {"ok": True}

@router.delete("/overhead-rules/{rid}")
def delete_overhead_rule(rid: int, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == rid).first()
    if not r: raise HTTPException(404, "规则不存在")
    db.delete(r); db.commit(); return {"ok": True}

@router.post("/overhead-rules/{rid}/toggle")
def toggle_overhead_rule(rid: int, db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    r = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == rid).first()
    if not r: raise HTTPException(404, "规则不存在")
    r.is_active = 0 if r.is_active else 1
    db.commit(); return {"ok": True, "is_active": r.is_active}

# ═══════════
# 产品间接费分摊
# ═══════════

@router.get("/product/{plan_id}/overhead-costs", response_model=List[OverheadCostOut])
def list_product_overhead(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP) -> list:
    return db.query(ProductOverheadCost).filter(
        ProductOverheadCost.product_plan_id == plan_id,
        ProductOverheadCost.period_id == period_id,
    ).all()

@router.post("/product/{plan_id}/allocate-overhead")
def allocate_overhead(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    """执行间接费分摊计算"""
    # 获取间接成本池总额
    indirect_cfg = db.query(IndirectCostConfig).filter(IndirectCostConfig.key == "default").first()
    total_pool = indirect_cfg.amount if indirect_cfg else 0
    if total_pool <= 0:
        raise HTTPException(400, "间接成本池总额未配置(IndirectCostConfig)，请先配置")

    # 获取启用的分摊规则
    rules = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.is_active == 1).order_by(OverheadAllocationRule.priority).all()
    if not rules:
        raise HTTPException(400, "没有启用的分摊规则")

    # 清空旧分摊结果
    db.query(ProductOverheadCost).filter(
        ProductOverheadCost.product_plan_id == plan_id,
        ProductOverheadCost.period_id == period_id,
    ).delete()

    # 获取该期间所有需分摊的产品
    products = db.query(CostAccountingSheet.product_plan_id).filter(
        CostAccountingSheet.period_id == period_id,
        CostAccountingSheet.product_plan_id == plan_id,
    ).distinct().all()
    if not products:
        # 如果还没有核算单，用 ProductPlan 作为产品列表
        products = db.query(ProductPlan.id).filter(ProductPlan.id == plan_id).all()
    product_ids = [p[0] for p in products]

    # 计算各产品的分摊基数总合
    base_totals = {}
    for pid in product_ids:
        sheet = db.query(CostAccountingSheet).filter(
            CostAccountingSheet.product_plan_id == pid,
            CostAccountingSheet.period_id == period_id,
        ).first()
        base_totals[pid] = {
            AllocationBase.DIRECT_LABOR.value: sheet.labor_cost_actual if sheet else 0,
            AllocationBase.DIRECT_MATERIAL.value: sheet.material_cost_actual if sheet else 0,
            AllocationBase.TOTAL_COST.value: sheet.total_cost_actual if sheet else 0,
            AllocationBase.QUANTITY.value: 1,  # 默认每个产品1个
        }

    # 按规则分摊
    created = []
    for rule in rules:
        base = rule.allocation_base
        # 计算所有产品的该基数总和
        all_base_sum = sum(b.get(base, 0) for b in base_totals.values())
        if all_base_sum <= 0:
            continue
        # 按比例分配间接成本池
        total_allocated = 0
        for pid in product_ids:
            prod_base = base_totals[pid].get(base, 0)
            ratio = prod_base / all_base_sum if all_base_sum > 0 else 0
            amount = round(total_pool * (rule.allocation_rate / 100) * ratio, 2)
            total_allocated += amount
            item = ProductOverheadCost(
                product_plan_id=pid, period_id=period_id, rule_id=rule.id,
                base_amount=prod_base, allocation_rate=rule.allocation_rate,
                allocation_amount=amount,
            )
            db.add(item)
            created.append(item)

    db.commit()
    return {"ok": True, "rules_used": len(rules), "allocated_count": len(created)}

# ═══════════
# 增强物料成本视图
# ═══════════

@router.get("/material-costs/enhanced/{bom_id}")
def get_enhanced_material_costs(bom_id: int, cost_type: str = Query("actual"), db: Session = Depends(get_db), _=_PERIOD_DEP) -> dict:
    """增强BOM成本树 — 层级小计/占比/Top物料"""
    from app.models.bom import BOM, BOMItem
    from collections import defaultdict

    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom: raise HTTPException(404, "BOM不存在")

    items = db.query(BOMItem).filter(BOMItem.bom_id == bom_id).all()
    children_map = defaultdict(list)
    for i in items: children_map[i.parent_item_id].append(i)

    LEVEL_NAMES = {1:"L1-整机", 2:"L2-内外机", 3:"L3-总成", 4:"L4-组件", 5:"L5-子件", 6:"L6-零部件"}
    level_costs = defaultdict(lambda: {"count": 0, "cost": 0.0})

    def calc_cost(item):
        up = float(getattr(item, "unit_price", 0) or 0)
        amt = float(getattr(item, "amount", 1) or 1)
        qty = float(item.quantity or 1)
        return round(up * amt * qty, 2)

    def build_tree(parent_id=None):
        nodes, total = [], 0.0
        for i in children_map.get(parent_id, []):
            c = calc_cost(i)
            child_nodes, child_total = build_tree(i.id)
            st = round(c + child_total, 2); total += st
            level_costs[i.level]["count"] += 1
            level_costs[i.level]["cost"] = round(level_costs[i.level]["cost"] + c, 2)
            nodes.append({
                "id": i.id, "part_no": i.part_no, "part_name": i.part_name,
                "item_type": i.item_type, "level": i.level,
                "quantity": float(i.quantity or 1), "unit": getattr(i, "unit", "个"),
                "unit_price": float(getattr(i, "unit_price", 0) or 0),
                "cost": c, "subtree_cost": st, "children": child_nodes,
            })
        return nodes, total

    tree, total = build_tree()
    cost_by_level = [{"level": l, "name": LEVEL_NAMES.get(l, f"L{l}"),
                      "count": v["count"], "cost": v["cost"],
                      "pct": round(v["cost"]/total*100, 1) if total > 0 else 0}
                     for l, v in sorted(level_costs.items())]

    # Top物料（按成本降序）
    flat = [{"id": i.id, "part_no": i.part_no, "part_name": i.part_name,
             "level": i.level, "cost": calc_cost(i)}
            for i in items]
    flat.sort(key=lambda x: x["cost"], reverse=True)
    top_items = flat[:10]

    return {
        "bom_id": bom_id, "bom_no": bom.bom_no, "product_code": bom.product_code,
        "total_cost": total, "cost_by_level": cost_by_level,
        "top_items": top_items, "tree": tree,
    }

