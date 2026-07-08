"""成本核算系统 — 核算单生成/定稿/重算模块

从 cost_accounting.py 拆分，减少主文件行数。
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan
from app.models.cost_accounting import (
    CostAccountingPeriod, CostAccountingSheet, CostAccountingItem,
    CostCategory, SheetStatus,
)
from app.models.project import Project
from app.models.bom import BOM
from app.models.product_plan import ProductPlanProjectLink

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost-accounting", tags=["cost-accounting-sheets"])
_DEP = Depends(require_menu("cost-accounting"))


def _gen_sheet_no() -> str:
    """生成核算单编号: CAS-YYYYMMDD-XXXX"""
    import random, string
    return f"CAS-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=4))}"


@router.get("/sheets")
def list_sheets(
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    period_id: Optional[int] = Query(None), status: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
    order_field: Optional[str] = Query(None), order_dir: Optional[str] = Query(None),
    db: Session = Depends(get_db), _=_DEP,
) -> dict:
    """列出核算单（可分页筛选排序）"""
    q = db.query(CostAccountingSheet)
    if period_id: q = q.filter(CostAccountingSheet.period_id == period_id)
    if status: q = q.filter(CostAccountingSheet.status == status)
    if plan_id: q = q.filter(CostAccountingSheet.product_plan_id == plan_id)
    total = q.count()
    if order_field and hasattr(CostAccountingSheet, order_field):
        col = getattr(CostAccountingSheet, order_field)
        q = q.order_by(col.desc() if order_dir == 'desc' else col.asc())
    else:
        q = q.order_by(desc(CostAccountingSheet.id))
    sheets = q.offset((page - 1) * size).limit(size).all()
    return {
        "items": [{c.key: getattr(s, c.key) for c in CostAccountingSheet.__table__.columns} for s in sheets],
        "total": total, "page": page, "size": size,
    }


@router.get("/sheets/{sid}")
def get_sheet(sid: int, db: Session = Depends(get_db), _=_DEP) -> dict:
    """获取核算单详情（含明细项）"""
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    items = db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == s.id).all()
    base = {c.key: getattr(s, c.key) for c in CostAccountingSheet.__table__.columns}
    base["items"] = [{c.key: getattr(i, c.key) for c in CostAccountingItem.__table__.columns} for i in items]
    return base


@router.post("/sheets/generate")
def generate_sheet(
    product_plan_id: str = Query(...), period_id: int = Query(...),
    bom_id: Optional[int] = Query(None),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _=_DEP,
) -> dict:
    """生成核算单 — 从BOM/人工/分摊汇总计算成本"""
    # 1. 验证期间
    period = db.query(CostAccountingPeriod).filter(CostAccountingPeriod.id == period_id).first()
    if not period: raise HTTPException(404, "核算期间不存在")
    # 2. 检查是否已存在
    existing = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == product_plan_id,
        CostAccountingSheet.period_id == period_id,
    ).first()
    if existing: raise HTTPException(400, f"该产品在该期间已有核算单: {existing.sheet_no}")
    # 3. 获取BOM物料成本
    material_actual = 0.0; material_target = 0.0
    target_bom = None
    if bom_id:
        target_bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not target_bom:
        plan = db.query(ProductPlan).filter(ProductPlan.id == product_plan_id).first()
        if not plan: raise HTTPException(404, "产品策划不存在")
        link = db.query(ProductPlanProjectLink).filter(
            ProductPlanProjectLink.product_plan_id == product_plan_id,
        ).first()
        project = None
        if link:
            project = db.query(Project).filter(Project.id == link.project_id).first()
        product_code = plan.code or (project.product_code if project else None)
        if product_code:
            target_bom = db.query(BOM).filter(
                BOM.product_code == product_code, BOM.status == "released",
            ).order_by(desc(BOM.created_at)).first()
    if target_bom:
        material_actual = target_bom.total_cost or 0
        material_target = target_bom.target_cost or 0
    # 4. 人工 + 制造费用（先计算，sheet 创建后补充）
    from app.models.cost_accounting import ProductLaborCost, ProductOverheadCost
    labor_sum = db.query(func.sum(ProductLaborCost.total_amount)).filter(
        ProductLaborCost.product_plan_id == product_plan_id,
        ProductLaborCost.period_id == period_id,
    ).scalar() or 0
    overhead_sum = db.query(func.sum(ProductOverheadCost.allocation_amount)).filter(
        ProductOverheadCost.product_plan_id == product_plan_id,
        ProductOverheadCost.period_id == period_id,
    ).scalar() or 0
    total_actual = round(material_actual + labor_sum + overhead_sum, 2)
    total_target = material_target
    variance = round(total_actual - total_target, 2)
    variance_pct = round(variance / total_target * 100, 2) if total_target else 0
    # 5. 创建核算单
    sheet = CostAccountingSheet(
        sheet_no=_gen_sheet_no(),
        product_plan_id=product_plan_id, period_id=period_id,
        material_cost_actual=material_actual, material_cost_target=material_target,
        labor_cost_actual=labor_sum, labor_cost_target=0,
        overhead_cost_actual=overhead_sum, overhead_cost_target=0,
        total_cost_actual=total_actual, total_cost_target=total_target,
        variance_amount=variance, variance_pct=variance_pct,
        created_by=current_user.username,
    )
    db.add(sheet)
    db.flush()
    # 6. 创建明细行
    items = []
    if material_actual > 0:
        items.append(CostAccountingItem(
            sheet_id=sheet.id, cost_category=CostCategory.MATERIAL.value,
            item_name="BOM物料成本合计", target_amount=material_target,
            actual_amount=material_actual,
            variance=round(material_actual - material_target, 2),
            source_type="bom",
        ))
    if labor_sum > 0:
        items.append(CostAccountingItem(
            sheet_id=sheet.id, cost_category=CostCategory.LABOR.value,
            item_name="人工工时成本合计", actual_amount=labor_sum,
            variance=labor_sum, source_type="labor",
        ))
    if overhead_sum > 0:
        items.append(CostAccountingItem(
            sheet_id=sheet.id, cost_category=CostCategory.OVERHEAD.value,
            item_name="制造费用分摊合计", actual_amount=overhead_sum,
            variance=overhead_sum, source_type="overhead",
        ))
    for it in items: db.add(it)
    db.commit()
    db.refresh(sheet)
    return {"id": sheet.id, "sheet_no": sheet.sheet_no, "status": sheet.status}


@router.post("/sheets/{sid}/finalize")
def finalize_sheet(sid: int, db: Session = Depends(get_db), _=_DEP) -> dict:
    """定稿核算单（锁定，不可修改）"""
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    if s.status == SheetStatus.FINALIZED.value: raise HTTPException(400, "核算单已定稿")
    s.status = SheetStatus.FINALIZED.value
    db.commit()
    return {"ok": True}


@router.post("/sheets/{sid}/recalculate")
def recalculate_sheet(sid: int, db: Session = Depends(get_db), _=_DEP) -> dict:
    """重新核算 — 重新获取BOM成本并更新"""
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    if s.status == SheetStatus.FINALIZED.value: raise HTTPException(400, "已定稿核算单不可重新核算")
    # 找最新BOM
    plan = db.query(ProductPlan).filter(ProductPlan.id == s.product_plan_id).first()
    if plan:
        link = db.query(ProductPlanProjectLink).filter(
            ProductPlanProjectLink.product_plan_id == s.product_plan_id,
        ).first()
        project = db.query(Project).filter(Project.id == link.project_id).first() if link else None
        product_code = plan.code or (project.product_code if project else None)
        if product_code:
            bom = db.query(BOM).filter(
                BOM.product_code == product_code, BOM.status == "released",
            ).order_by(desc(BOM.created_at)).first()
            if bom:
                s.material_cost_actual = bom.total_cost or 0
                s.material_cost_target = bom.target_cost or 0
                total_actual = round((bom.total_cost or 0) + s.labor_cost_actual + s.overhead_cost_actual, 2)
                s.total_cost_actual = total_actual
                s.total_cost_target = s.material_cost_target
                s.variance_amount = round(total_actual - s.material_cost_target, 2)
                s.variance_pct = round(s.variance_amount / s.material_cost_target * 100, 2) if s.material_cost_target else 0
    db.commit()
    return {"ok": True}


@router.delete("/sheets/{sid}")
def delete_sheet(sid: int, db: Session = Depends(get_db), _=_DEP) -> dict:
    """删除核算单"""
    s = db.query(CostAccountingSheet).filter(CostAccountingSheet.id == sid).first()
    if not s: raise HTTPException(404, "核算单不存在")
    if s.status == SheetStatus.FINALIZED.value: raise HTTPException(400, "已定稿核算单不可删除")
    db.delete(s); db.commit(); return {"ok": True}
