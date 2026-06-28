"""成本核算系统 — 差异分析模块

从 cost_accounting.py 拆分，减少主文件行数（688→563行）。
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_menu
from app.models.cost_accounting import CostAccountingSheet, CostAccountingItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cost-accounting", tags=["cost-accounting-analysis"])
_DEP = Depends(require_menu("cost-accounting"))


@router.get("/analysis/variance")
def get_variance_analysis(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_DEP) -> dict:
    """成本差异分析 — 料工费三维度对比"""
    sheet = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == plan_id,
        CostAccountingSheet.period_id == period_id,
    ).first()
    if not sheet:
        raise HTTPException(404, "该产品在该期间无核算单")
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
def get_variance_detail(plan_id: str, period_id: int = Query(...), db: Session = Depends(get_db), _=_DEP) -> dict:
    """成本差异明细 — 每个核算单项的差异"""
    sheet = db.query(CostAccountingSheet).filter(
        CostAccountingSheet.product_plan_id == plan_id,
        CostAccountingSheet.period_id == period_id,
    ).first()
    if not sheet:
        raise HTTPException(404, "核算单不存在")
    items = db.query(CostAccountingItem).filter(CostAccountingItem.sheet_id == sheet.id).all()
    return {"sheet_no": sheet.sheet_no, "items": [
        {"id": i.id, "category": i.cost_category, "name": i.item_name,
         "target": i.target_amount, "actual": i.actual_amount,
         "variance": i.variance, "variance_pct": i.variance_pct}
        for i in items
    ]}


@router.get("/analysis/trend")
def get_cost_trend(plan_id: str, limit: int = Query(6), db: Session = Depends(get_db), _=_DEP) -> list:
    """成本趋势 — 多个核算期间的成本变化"""
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
