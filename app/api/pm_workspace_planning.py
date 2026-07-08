"""PM工作台 — 年度规划 CRUD (P2.1 ~ P2.3)"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.project import Project
from app.models.annual_plan import AnnualPlan
from app.api.pm_workspace import _require_pm

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pm", tags=["产品经理工作台"])


def _planning_item_to_dict(ap: AnnualPlan, project_count: int = 0) -> dict:
    """将 AnnualPlan ORM 对象转为包含 project_count 的 dict"""
    return {
        "id": ap.id, "name": ap.name, "year": ap.year,
        "description": ap.description, "doc_ref": ap.doc_ref,
        "owner": ap.owner, "project_count": project_count,
        "created_at": str(ap.created_at) if ap.created_at else None,
        "updated_at": str(ap.updated_at) if ap.updated_at else None,
    }


@router.get("/planning-items")
def list_planning_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> list:
    """获取年度规划列表"""
    plans = db.query(AnnualPlan).order_by(AnnualPlan.year.desc(), AnnualPlan.created_at.desc()).all()
    result = []
    for ap in plans:
        project_count = 0
        result.append(_planning_item_to_dict(ap, project_count))
    return result


@router.post("/planning-items")
def create_planning_item(
    name: str = Body(..., max_length=200),
    year: int = Body(...),
    description: str | None = Body(None),
    doc_ref: str | None = Body(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """创建年度规划条目"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="规划名称不能为空")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="请输入有效的年度")
    existing = db.query(AnnualPlan).filter(AnnualPlan.name == name.strip(), AnnualPlan.year == year).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"年度 {year} 下已存在同名规划 '{name}'")
    ap = AnnualPlan(name=name.strip(), year=year, description=description, doc_ref=doc_ref, owner=current_user.username)
    try:
        db.add(ap)
        db.commit()
        db.refresh(ap)
    except Exception as e:
        logger.exception("unexpected error")
        db.rollback()
        logger.error(f"PM年度规划创建失败: {e}")
        raise
    return _planning_item_to_dict(ap, 0)


@router.put("/planning-items/{plan_id}")
def update_planning_item(
    plan_id: int,
    name: str | None = Body(None, max_length=200),
    year: int | None = Body(None),
    description: str | None = Body(None),
    doc_ref: str | None = Body(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """更新年度规划条目"""
    ap = db.query(AnnualPlan).filter(AnnualPlan.id == plan_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="年度规划不存在")
    if ap.owner != current_user.username:
        raise HTTPException(status_code=403, detail="无权修改他人的年度规划")
    try:
        if name is not None:
            if not name.strip():
                raise HTTPException(status_code=400, detail="规划名称不能为空")
            ap.name = name.strip()
        if year is not None:
            if year < 2000 or year > 2100:
                raise HTTPException(status_code=400, detail="请输入有效的年度")
            ap.year = year
        if description is not None:
            ap.description = description
        if doc_ref is not None:
            ap.doc_ref = doc_ref
        db.commit()
        db.refresh(ap)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("unexpected error")
        db.rollback()
        logger.error(f"PM年度规划更新失败: {e}")
        raise
    project_count = 0
    return _planning_item_to_dict(ap, project_count)


@router.delete("/planning-items/{plan_id}")
def delete_planning_item(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """删除年度规划条目"""
    ap = db.query(AnnualPlan).filter(AnnualPlan.id == plan_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="年度规划不存在")
    if ap.owner != current_user.username:
        raise HTTPException(status_code=403, detail="无权删除他人的年度规划")
    if db.query(Project).filter(Project.annual_planning_ref == ap.name, Project.is_deleted == False).count() > 0:
        raise HTTPException(status_code=409, detail="该规划下存在关联项目，请先解除关联后再删除")
    try:
        db.delete(ap)
        db.commit()
    except Exception as e:
        logger.exception("unexpected error")
        db.rollback()
        logger.error(f"PM年度规划删除失败: {e}")
        raise
    return {"detail": "年度规划已删除"}
