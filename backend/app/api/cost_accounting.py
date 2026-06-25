"""成本核算系统 API — 期间/费率/分摊/核算单/差异分析/导出"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List
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

router = APIRouter(prefix="/api/cost-accounting", tags=["cost-accounting"])

_PERIOD_DEP = Depends(require_menu("cost-accounting"))


# ════════════════════════════════════════
# Schemas
# ════════════════════════════════════════

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


# ════════════════════════════════════════
# 核算期间管理
# ════════════════════════════════════════

@router.get("/periods", response_model=List[PeriodOut])
def list_periods(db: Session = Depends(get_db), _=_PERIOD_DEP):
    return db.query(CostAccountingPeriod).order_by(desc(CostAccountingPeriod.start_date)).all()

@router.post("/periods", response_model=PeriodOut)
def create_period(data: PeriodCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    p = CostAccountingPeriod(period_name=data.period_name, start_date=data.start_date, end_date=data.end_date)
    db.add(p); db.commit(); db.refresh(p); return p

@router.patch("/periods/{pid}", response_model=PeriodOut)
def update_period(pid: int, data: PeriodCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    p = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == pid).first()
    if not p: raise HTTPException(404, "期间不存在")
    if p.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "已关闭期间不可修改")
    p.period_name = data.period_name; p.start_date = data.start_date; p.end_date = data.end_date
    db.commit(); db.refresh(p); return p

@router.delete("/periods/{pid}")
def delete_period(pid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    p = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == pid).first()
    if not p: raise HTTPException(404, "期间不存在")
    if p.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "已关闭期间不可删除")
    db.delete(p); db.commit(); return {"ok": True}

@router.post("/periods/{pid}/close", response_model=PeriodOut)
def close_period(pid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    p = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == pid).first()
    if not p: raise HTTPException(404, "期间不存在")
    if p.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "期间已关闭")
    p.status = PeriodStatus.CLOSED.value; db.commit(); db.refresh(p); return p


# ════════════════════════════════════════
# 工时费率配置
# ════════════════════════════════════════

@router.get("/labor-rates", response_model=List[LaborRateOut])
def list_labor_rates(db: Session = Depends(get_db), _=_PERIOD_DEP):
    return db.query(LaborRateConfig).order_by(LaborRateConfig.operation_code).all()

@router.post("/labor-rates", response_model=LaborRateOut)
def create_labor_rate(data: LaborRateCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = LaborRateConfig(operation_code=data.operation_code, operation_name=data.operation_name, hourly_rate=data.hourly_rate)
    db.add(r); db.commit(); db.refresh(r); return r

@router.patch("/labor-rates/{rid}")
def update_labor_rate(rid: int, data: LaborRateCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(LaborRateConfig).filter(LaborRateConfig.id == rid).first()
    if not r: raise HTTPException(404, "费率不存在")
    for k, v in data.dict().items(): setattr(r, k, v)
    db.commit(); return {"ok": True}

@router.delete("/labor-rates/{rid}")
def delete_labor_rate(rid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(LaborRateConfig).filter(LaborRateConfig.id == rid).first()
    if not r: raise HTTPException(404, "费率不存在")
    db.delete(r); db.commit(); return {"ok": True}


# ════════════════════════════════════════
# 产品人工成本
# ════════════════════════════════════════

@router.get("/product/{plan_id}/labor-costs", response_model=List[LaborCostOut])
def list_product_labor(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
    q = db.query(ProductLaborCost).filter(
        ProductLaborCost.product_plan_id == plan_id,
        ProductLaborCost.period_id == period_id,
    ).order_by(ProductLaborCost.operation_code).all()
    return q

@router.post("/product/{plan_id}/labor-costs", response_model=LaborCostOut)
def create_product_labor(plan_id: str, period_id: int = Query(...), data: LaborCostCreate = Body(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = ProductLaborCost(
        product_plan_id=plan_id, period_id=period_id,
        operation_code=data.operation_code, operation_name=data.operation_name,
        labor_hours=data.labor_hours, hourly_rate=data.hourly_rate,
        total_amount=round(data.labor_hours * data.hourly_rate, 2),
    )
    db.add(r); db.commit(); db.refresh(r); return r

@router.patch("/product/{plan_id}/labor-costs/{lid}")
def update_product_labor(lid: int, data: LaborCostCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(ProductLaborCost).filter(ProductLaborCost.id == lid).first()
    if not r: raise HTTPException(404, "记录不存在")
    r.labor_hours = data.labor_hours; r.hourly_rate = data.hourly_rate
    r.operation_code = data.operation_code; r.operation_name = data.operation_name
    r.total_amount = round(data.labor_hours * data.hourly_rate, 2)
    db.commit(); return {"ok": True}

@router.delete("/product/{plan_id}/labor-costs/{lid}")
def delete_product_labor(lid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(ProductLaborCost).filter(ProductLaborCost.id == lid).first()
    if not r: raise HTTPException(404, "记录不存在")
    db.delete(r); db.commit(); return {"ok": True}

@router.post("/product/{plan_id}/calculate-labor")
def calculate_labor(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
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


# ════════════════════════════════════════
# 间接费分摊规则
# ════════════════════════════════════════

@router.get("/overhead-rules", response_model=List[OverheadRuleOut])
def list_overhead_rules(db: Session = Depends(get_db), _=_PERIOD_DEP):
    return db.query(OverheadAllocationRule).order_by(OverheadAllocationRule.priority).all()

@router.post("/overhead-rules", response_model=OverheadRuleOut)
def create_overhead_rule(data: OverheadRuleCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = OverheadAllocationRule(
        rule_name=data.rule_name, allocation_base=data.allocation_base,
        allocation_rate=data.allocation_rate, description=data.description,
        priority=data.priority,
    )
    db.add(r); db.commit(); db.refresh(r); return r

@router.patch("/overhead-rules/{rid}")
def update_overhead_rule(rid: int, data: OverheadRuleCreate, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == rid).first()
    if not r: raise HTTPException(404, "规则不存在")
    for k, v in data.dict().items(): setattr(r, k, v)
    db.commit(); return {"ok": True}

@router.delete("/overhead-rules/{rid}")
def delete_overhead_rule(rid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == rid).first()
    if not r: raise HTTPException(404, "规则不存在")
    db.delete(r); db.commit(); return {"ok": True}

@router.post("/overhead-rules/{rid}/toggle")
def toggle_overhead_rule(rid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    r = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == rid).first()
    if not r: raise HTTPException(404, "规则不存在")
    r.is_active = 0 if r.is_active else 1
    db.commit(); return {"ok": True, "is_active": r.is_active}


# ════════════════════════════════════════
# 产品间接费分摊
# ════════════════════════════════════════

@router.get("/product/{plan_id}/overhead-costs", response_model=List[OverheadCostOut])
def list_product_overhead(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
    return db.query(ProductOverheadCost).filter(
        ProductOverheadCost.product_plan_id == plan_id,
        ProductOverheadCost.period_id == period_id,
    ).all()

@router.post("/product/{plan_id}/allocate-overhead")
def allocate_overhead(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
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


# ════════════════════════════════════════
# 增强物料成本视图
# ════════════════════════════════════════

@router.get("/material-costs/enhanced/{bom_id}")
def get_enhanced_material_costs(bom_id: int, cost_type: str = Query("actual"), db: Session = Depends(get_db), _=_PERIOD_DEP):
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


# ════════════════════════════════════════
# 成本核算单（核心）
# ════════════════════════════════════════

def _gen_sheet_no() -> str:
    dt = date.today().strftime("%Y%m%d")
    rand = ''.join(random.choices(string.digits, k=3))
    return f"CAS-{dt}-{rand}"

@router.post("/sheets/generate")
def generate_sheet(
    product_plan_id: str = Body(...), period_id: int = Body(...),
    bom_id: Optional[int] = Body(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """自动生成成本核算单 — 聚合料/工/费三大要素"""
    # 验证产品和期间
    plan = db.query(ProductPlan).filter(ProductPlan.id == product_plan_id).first()
    if not plan: raise HTTPException(404, "产品策划不存在")
    period = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == period_id).first()
    if not period: raise HTTPException(404, "核算期间不存在")
    if period.status == PeriodStatus.CLOSED.value: raise HTTPException(400, "已关闭期间不能生成核算单")

    # 检查是否已存在
    existing = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == product_plan_id,
        CostAccountingSheet.period_id == period_id,
    ).first()
    if existing:
        raise HTTPException(400, f"该产品在该期间已有核算单({existing.sheet_no})，请使用重新核算")

    # 1. 物料成本 — 通过Project→product_code→BOM链路
    material_actual = 0.0
    material_target = 0.0
    if plan.project_id:
        from app.models.project import Project
        project = db.query(Project).filter(Project.id == plan.project_id).first()
        if project and project.product_code:
            from app.models.bom import BOM
            bom = db.query(BOM).filter(BOM.product_code == project.product_code)
            if bom_id: bom = bom.filter(BOM.id == bom_id)
            else: bom = bom.order_by(desc(BOM.created_at)).first()
            if isinstance(bom, type(db.query(BOM))): bom = bom.first()
            if not bom and bom_id:
                bom = db.query(BOM).filter(BOM.id == bom_id).first()
            if bom:
                from app.api.bom import get_bom_cost_summary
                try:
                    summary = get_bom_cost_summary(bom.id, db)
                    if isinstance(summary, dict):
                        material_actual = float(summary.get("total_cost", 0))
                except Exception:
                    pass

    # 解析目标成本
    if plan.cost_target:
        import json
        try:
            ct = json.loads(plan.cost_target) if isinstance(plan.cost_target, str) else plan.cost_target
            material_target = float(ct.get("target", 0)) if isinstance(ct, dict) else 0
        except (json.JSONDecodeError, TypeError, ValueError):
            material_target = 0

    # 2. 人工成本
    labor_records = db.query(ProductLaborCost).filter(
        ProductLaborCost.product_plan_id == product_plan_id,
        ProductLaborCost.period_id == period_id,
    ).all()
    labor_actual = round(sum(r.total_amount for r in labor_records), 2)

    # 3. 制造费用分摊
    overhead_records = db.query(ProductOverheadCost).filter(
        ProductOverheadCost.product_plan_id == product_plan_id,
        ProductOverheadCost.period_id == period_id,
    ).all()
    overhead_actual = round(sum(r.allocation_amount for r in overhead_records), 2)

    # 4. 计算汇总
    total_actual = round(material_actual + labor_actual + overhead_actual, 2)
    total_target = material_target  # 简化：目标成本只用物料目标
    variance = round(total_actual - total_target, 2)
    variance_pct = round(variance / total_target * 100, 2) if total_target else 0

    # 5. 创建核算单
    sheet = CostAccountingSheet(
        sheet_no=_gen_sheet_no(),
        product_plan_id=product_plan_id, period_id=period_id,
        material_cost_actual=material_actual, material_cost_target=material_target,
        labor_cost_actual=labor_actual, labor_cost_target=0,
        overhead_cost_actual=overhead_actual, overhead_cost_target=0,
        total_cost_actual=total_actual, total_cost_target=total_target,
        variance_amount=variance, variance_pct=variance_pct,
        created_by=current_user.username,
    )
    db.add(sheet)
    db.flush()  # 获取 ID

    # 6. 创建明细行
    items = []
    # 物料明细
    if material_actual > 0:
        items.append(CostAccountingItem(
            sheet_id=sheet.id, cost_category=CostCategory.MATERIAL.value,
            item_name="BOM物料成本合计", target_amount=material_target,
            actual_amount=material_actual,
            variance=round(material_actual - material_target, 2),
            source_type="bom",
        ))
    # 人工明细
    for lr in labor_records:
        items.append(CostAccountingItem(
            sheet_id=sheet.id, cost_category=CostCategory.LABOR.value,
            item_name=lr.operation_name, target_amount=0,
            actual_amount=lr.total_amount, variance=lr.total_amount,
            source_type="labor_record", source_id=lr.id,
        ))
    # 费用明细
    for oc in overhead_records:
        rule = db.query(OverheadAllocationRule).filter(OverheadAllocationRule.id == oc.rule_id).first()
        items.append(CostAccountingItem(
            sheet_id=sheet.id, cost_category=CostCategory.OVERHEAD.value,
            item_name=rule.rule_name if rule else "制造费用分摊",
            target_amount=0, actual_amount=oc.allocation_amount,
            variance=oc.allocation_amount,
            source_type="overhead_rule", source_id=oc.id,
        ))

    for it in items: db.add(it)
    db.commit()
    db.refresh(sheet)
    return {"ok": True, "sheet_id": sheet.id, "sheet_no": sheet.sheet_no}

@router.get("/sheets", response_model=List[SheetOut])
def list_sheets(
    plan_id: Optional[str] = Query(None), period_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None), page: int = Query(1), size: int = Query(20),
    db: Session = Depends(get_db), _=_PERIOD_DEP,
):
    q = db.query(CostAccountingSheet)
    if plan_id: q = q.filter(CostAccountingSheet.product_plan_id == plan_id)
    if period_id: q = q.filter(CostAccountingSheet.period_id == period_id)
    if status: q = q.filter(CostAccountingSheet.status == status)
    total = q.count()
    sheets = q.order_by(desc(CostAccountingSheet.created_at)).offset((page-1)*size).limit(size).all()
    # eager load items
    result = []
    for s in sheets:
        s_dict = s.__dict__
        items_list = db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == s.id).all()
        s_dict["items"] = items_list
        result.append(s_dict)
    return result

@router.get("/sheets/{sid}", response_model=SheetOut)
def get_sheet_detail(sid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    items_list = db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == s.id).all()
    s.items = items_list
    return s

@router.post("/sheets/{sid}/finalize")
def finalize_sheet(sid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    if s.status == SheetStatus.FINALIZED.value:
        raise HTTPException(400, "核算单已定稿")
    s.status = SheetStatus.FINALIZED.value; db.commit(); return {"ok": True}

@router.post("/sheets/{sid}/recalculate")
def recalculate_sheet(sid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    """重新核算 — 重新聚合料工费数据"""
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    if s.status == SheetStatus.FINALIZED.value:
        raise HTTPException(400, "已定稿核算单不可重新核算")
    # 重新聚合（简化版：重新计算人工和费用，物料保持不变）
    labor_records = db.query(ProductLaborCost).filter(
        ProductLaborCost.product_plan_id == s.product_plan_id,
        ProductLaborCost.period_id == s.period_id,
    ).all()
    overhead_records = db.query(ProductOverheadCost).filter(
        ProductOverheadCost.product_plan_id == s.product_plan_id,
        ProductOverheadCost.period_id == s.period_id,
    ).all()
    s.labor_cost_actual = round(sum(r.total_amount for r in labor_records), 2)
    s.overhead_cost_actual = round(sum(r.allocation_amount for r in overhead_records), 2)
    s.total_cost_actual = round(s.material_cost_actual + s.labor_cost_actual + s.overhead_cost_actual, 2)
    s.variance_amount = round(s.total_cost_actual - s.total_cost_target, 2)
    s.variance_pct = round(s.variance_amount / s.total_cost_target * 100, 2) if s.total_cost_target else 0
    # 更新明细
    db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == s.id).delete()
    items = []
    # 物料明细（保留原有值）
    if s.material_cost_actual > 0:
        items.append(CostAccountingItem(sheet_id=s.id, cost_category=CostCategory.MATERIAL.value,
            item_name="BOM物料成本合计", target_amount=s.material_cost_target,
            actual_amount=s.material_cost_actual,
            variance=round(s.material_cost_actual - s.material_cost_target, 2),
            source_type="bom"))
    # 人工明细
    if s.labor_cost_actual > 0:
        for lr in labor_records:
            items.append(CostAccountingItem(sheet_id=s.id, cost_category=CostCategory.LABOR.value,
                item_name=lr.operation_name, actual_amount=lr.total_amount, variance=lr.total_amount,
                source_type="labor_record", source_id=lr.id))
    if s.overhead_cost_actual > 0:
        for oc in overhead_records:
            items.append(CostAccountingItem(sheet_id=s.id, cost_category=CostCategory.OVERHEAD.value,
                item_name=f"分摊({oc.rule_id})", actual_amount=oc.allocation_amount,
                variance=oc.allocation_amount, source_type="overhead_rule", source_id=oc.id))
    for it in items: db.add(it)
    db.commit()
    return {"ok": True, "sheet_id": s.id}

@router.delete("/sheets/{sid}")
def delete_sheet(sid: int, db: Session = Depends(get_db), _=_PERIOD_DEP):
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    if s.status == SheetStatus.FINALIZED.value: raise HTTPException(400, "已定稿核算单不可删除")
    db.delete(s); db.commit(); return {"ok": True}


# ════════════════════════════════════════
# 成本差异分析
# ════════════════════════════════════════

@router.get("/analysis/variance")
def get_variance_analysis(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
    sheet = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == plan_id,
        CostAccountingSheet.period_id == period_id,
    ).first()
    if not sheet: raise HTTPException(404, "该产品在该期间无核算单")
    return {
        "sheet_id": sheet.id, "sheet_no": sheet.sheet_no,
        "material": {"actual": sheet.material_cost_actual, "target": sheet.material_cost_target,
                      "variance": sheet.material_cost_actual - sheet.material_cost_target,
                      "variance_pct": round((sheet.material_cost_actual - sheet.material_cost_target) / sheet.material_cost_target * 100, 2) if sheet.material_cost_target else 0},
        "labor": {"actual": sheet.labor_cost_actual, "target": sheet.labor_cost_target,
                  "variance": sheet.labor_cost_actual - sheet.labor_cost_target,
                  "variance_pct": round((sheet.labor_cost_actual - sheet.labor_cost_target) / sheet.labor_cost_target * 100, 2) if sheet.labor_cost_target else 0},
        "overhead": {"actual": sheet.overhead_cost_actual, "target": sheet.overhead_cost_target,
                     "variance": sheet.overhead_cost_actual - sheet.overhead_cost_target,
                     "variance_pct": round((sheet.overhead_cost_actual - sheet.overhead_cost_target) / sheet.overhead_cost_target * 100, 2) if sheet.overhead_cost_target else 0},
        "total": {"actual": sheet.total_cost_actual, "target": sheet.total_cost_target,
                  "variance": sheet.variance_amount, "variance_pct": sheet.variance_pct},
    }

@router.get("/analysis/detail")
def get_variance_detail(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
    sheet = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == plan_id,
        CostAccountingSheet.period_id == period_id,
    ).first()
    if not sheet: raise HTTPException(404, "核算单不存在")
    items = db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == sheet.id).all()
    return {"sheet_no": sheet.sheet_no, "items": [
        {"id": i.id, "category": i.cost_category, "name": i.item_name,
         "target": i.target_amount, "actual": i.actual_amount,
         "variance": i.variance, "variance_pct": i.variance_pct}
        for i in items
    ]}

@router.get("/analysis/trend")
def get_cost_trend(plan_id: str, limit: int = Query(6), db: Session = Depends(get_db), _=_PERIOD_DEP):
    sheets = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == plan_id,
    ).order_by(CostAccountingSheet.period_id).limit(limit).all()
    return [
        {"period_id": s.period_id, "sheet_no": s.sheet_no, "status": s.status,
         "material_actual": s.material_cost_actual, "labor_actual": s.labor_cost_actual,
         "overhead_actual": s.overhead_cost_actual, "total_actual": s.total_cost_actual,
         "total_target": s.total_cost_target, "variance_pct": s.variance_pct}
        for s in sheets
    ]


# ════════════════════════════════════════
# 报告导出（CSV）
# ════════════════════════════════════════

@router.get("/reports/export/csv")
def export_csv(sheet_id: int = Query(...), db: Session = Depends(get_db), _=_PERIOD_DEP):
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sheet_id).first()
    if not s: raise HTTPException(404, "核算单不存在")
    items = db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == s.id).all()
    import csv, io
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["核算单", s.sheet_no, "", "", "", ""])
    w.writerow(["成本类别", "项目名称", "目标金额", "实际金额", "差异", "差异率%"])
    w.writerow(["物料成本", "BOM物料合计", s.material_cost_target, s.material_cost_actual,
                 s.material_cost_actual - s.material_cost_target, ""])
    for i in items:
        w.writerow([i.cost_category, i.item_name, i.target_amount, i.actual_amount, i.variance, i.variance_pct])
    w.writerow(["合计", "", s.total_cost_target, s.total_cost_actual, s.variance_amount, s.variance_pct])
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={s.sheet_no}.csv"},
    )
