"""manufacturability API 别名 — 兼容前端旧路径 /api/manufacturability → /api/dfm"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.manufacturability import (
    DFMChecklist, DFMReport, DFMReportItem, DFMScoreWeight,
)
from app.schemas.manufacturability import (
    DFMChecklistCreate, DFMChecklistUpdate, DFMChecklistOut, DFMChecklistListOut,
    DFMReportCreate, DFMReportUpdate, DFMReportOut, DFMReportListOut,
    DFMReportItemCreate, DFMReportItemUpdate, DFMReportItemOut,
    DFMScoreWeightCreate, DFMScoreWeightUpdate, DFMScoreWeightOut, DFMScoreWeightListOut,
    DFMScoreResult,
)

# Re-use the score calculation from the original module
from app.api.manufacturability import calculate_dfm_score

router = APIRouter(prefix="/api/manufacturability", tags=["DFM可制造性分析"])


# ── 检查项模板 ──

@router.get("/checklist", response_model=DFMChecklistListOut)
def list_checklist(
    product_type: Optional[str] = Query(None),
    dfm_category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DFMChecklist)
    if product_type:
        q = q.filter(DFMChecklist.product_type == product_type)
    if dfm_category:
        q = q.filter(DFMChecklist.dfm_category == dfm_category)
    total = q.count()
    items = q.order_by(DFMChecklist.id).offset((page - 1) * page_size).limit(page_size).all()
    return DFMChecklistListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/checklist", response_model=DFMChecklistOut, status_code=201)
def create_checklist_item(
    data: DFMChecklistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "engineer")),
):
    item = DFMChecklist(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/checklist/{item_id}", response_model=DFMChecklistOut)
def get_checklist_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(DFMChecklist).filter(DFMChecklist.id == item_id).first()
    if not item:
        raise HTTPException(404, "检查项不存在")
    return item


@router.put("/checklist/{item_id}", response_model=DFMChecklistOut)
def update_checklist_item(
    item_id: int,
    data: DFMChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "engineer")),
):
    item = db.query(DFMChecklist).filter(DFMChecklist.id == item_id).first()
    if not item:
        raise HTTPException(404, "检查项不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


# ── 评估报告 ──

@router.get("/reports", response_model=DFMReportListOut)
def list_reports(
    product_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DFMReport)
    if product_id:
        q = q.filter(DFMReport.product_id == product_id)
    if status:
        q = q.filter(DFMReport.status == status)
    total = q.count()
    items = q.order_by(DFMReport.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return DFMReportListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/reports", response_model=DFMReportOut, status_code=201)
def create_report(
    data: DFMReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "engineer")),
):
    report = DFMReport(**data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports/{report_id}", response_model=DFMReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(DFMReport).filter(DFMReport.id == report_id).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    return report


@router.get("/reports/{report_id}/score", response_model=DFMScoreResult)
def get_report_score(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return calculate_dfm_score(db, report_id)


@router.get("/reports/{report_id}/items", response_model=list[DFMReportItemOut])
def list_report_items(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(DFMReportItem).filter(DFMReportItem.report_id == report_id).all()


@router.post("/reports/{report_id}/items", response_model=DFMReportItemOut, status_code=201)
def add_report_item(
    report_id: int,
    data: DFMReportItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "engineer")),
):
    item = DFMReportItem(report_id=report_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/reports/{report_id}/items/{item_id}", response_model=DFMReportItemOut)
def update_report_item(
    report_id: int,
    item_id: int,
    data: DFMReportItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "engineer")),
):
    item = db.query(DFMReportItem).filter(DFMReportItem.id == item_id, DFMReportItem.report_id == report_id).first()
    if not item:
        raise HTTPException(404, "检查项不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/reports/{report_id}", response_model=DFMReportOut)
def update_report(
    report_id: int,
    data: DFMReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "engineer")),
):
    report = db.query(DFMReport).filter(DFMReport.id == report_id).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(report, k, v)
    db.commit()
    db.refresh(report)
    return report


# ── 评分权重 ──

@router.get("/score-weights", response_model=DFMScoreWeightListOut)
def list_score_weights(
    product_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(DFMScoreWeight)
    if product_type:
        q = q.filter(DFMScoreWeight.product_type == product_type)
    items = q.order_by(DFMScoreWeight.id).all()
    return DFMScoreWeightListOut(items=items)


@router.post("/score-weights", response_model=DFMScoreWeightOut, status_code=201)
def create_score_weight(
    data: DFMScoreWeightCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    w = DFMScoreWeight(**data.model_dump())
    db.add(w)
    db.commit()
    db.refresh(w)
    return w
