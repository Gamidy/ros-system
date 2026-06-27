"""ProductPlan Review API — P4复盘

3个端点：
- POST /product-plans/{plan_id}/review — 提交复盘
- GET  /product-plans/{plan_id}/review — 查看复盘
- PUT  /product-plans/{plan_id}/review — 更新复盘
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan, ProductPlanReview

router = APIRouter(prefix="/product-plans", tags=["产品策划"])


# ── Schemas ──

class ReviewCreate(BaseModel):
    """创建复盘请求"""
    review_date: Optional[str] = None
    actual_cost_total: Optional[Decimal] = None
    cost_variance_pct: Optional[float] = None
    actual_launch_date: Optional[str] = None
    schedule_variance_days: Optional[int] = None
    market_feedback: Optional[str] = None
    lessons_learned: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    reviewer_id: Optional[str] = None
    review_template_id: Optional[str] = None


class ReviewUpdate(BaseModel):
    """更新复盘请求"""
    review_date: Optional[str] = None
    actual_cost_total: Optional[Decimal] = None
    cost_variance_pct: Optional[float] = None
    actual_launch_date: Optional[str] = None
    schedule_variance_days: Optional[int] = None
    market_feedback: Optional[str] = None
    lessons_learned: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    reviewer_id: Optional[str] = None
    review_template_id: Optional[str] = None


class ReviewOut(BaseModel):
    """复盘输出"""
    id: str
    product_plan_id: str
    review_date: Optional[str] = None
    actual_cost_total: Optional[float] = None
    cost_variance_pct: Optional[float] = None
    actual_launch_date: Optional[str] = None
    schedule_variance_days: Optional[int] = None
    market_feedback: Optional[str] = None
    lessons_learned: Optional[str] = None
    rating: Optional[int] = None
    reviewer_id: Optional[str] = None
    review_template_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── 辅助函数 ──

def _review_to_dict(review: ProductPlanReview) -> dict:
    """将 ProductPlanReview ORM 转为响应 dict"""
    return {
        "id": review.id,
        "product_plan_id": review.product_plan_id,
        "review_date": str(review.review_date) if review.review_date else None,
        "actual_cost_total": float(review.actual_cost_total) if review.actual_cost_total else None,
        "cost_variance_pct": review.cost_variance_pct,
        "actual_launch_date": str(review.actual_launch_date) if review.actual_launch_date else None,
        "schedule_variance_days": review.schedule_variance_days,
        "market_feedback": review.market_feedback,
        "lessons_learned": review.lessons_learned,
        "rating": review.rating,
        "reviewer_id": review.reviewer_id,
        "review_template_id": review.review_template_id,
        "created_at": str(review.created_at) if review.created_at else None,
        "updated_at": str(review.updated_at) if review.updated_at else None,
    }


def _parse_datetime(val: Optional[str]) -> Optional[datetime]:
    """将 ISO 字符串解析为 datetime，无效则返回 None"""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val: Optional[str]) -> Optional[date]:
    """将 ISO 日期字符串解析为 date，无效则返回 None"""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val).date()
    except (ValueError, TypeError):
        return None


# ── API 端点 ──

@router.post("/{plan_id}/review", response_model=ReviewOut)
def create_review(
    plan_id: str,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """提交复盘 — 每个策划最多一条复盘记录"""
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        existing = db.query(ProductPlanReview).filter(
            ProductPlanReview.product_plan_id == plan_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="该策划已有复盘记录，请使用 PUT 更新")

        review = ProductPlanReview(
            product_plan_id=plan_id,
            review_date=_parse_datetime(data.review_date) or datetime.now(),
            actual_cost_total=data.actual_cost_total,
            cost_variance_pct=data.cost_variance_pct,
            actual_launch_date=_parse_date(data.actual_launch_date),
            schedule_variance_days=data.schedule_variance_days,
            market_feedback=data.market_feedback,
            lessons_learned=data.lessons_learned,
            rating=data.rating,
            reviewer_id=data.reviewer_id or current_user.username,
            review_template_id=data.review_template_id,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return _review_to_dict(review)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建复盘失败: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建复盘失败: {str(e)}")


@router.get("/{plan_id}/review", response_model=ReviewOut)
def get_review(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """查看策划复盘记录"""
    try:
        review = db.query(ProductPlanReview).filter(
            ProductPlanReview.product_plan_id == plan_id
        ).first()
        if not review:
            raise HTTPException(status_code=404, detail="复盘记录不存在")

        return _review_to_dict(review)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询复盘失败: {str(e)}")


@router.put("/{plan_id}/review", response_model=ReviewOut)
def update_review(
    plan_id: str,
    data: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """更新复盘记录"""
    try:
        review = db.query(ProductPlanReview).filter(
            ProductPlanReview.product_plan_id == plan_id
        ).first()
        if not review:
            raise HTTPException(status_code=404, detail="复盘记录不存在，请先 POST 创建")

        update_data = data.model_dump(exclude_unset=True)
        field_map = {
            "review_date": _parse_datetime(update_data.pop("review_date", None)) if "review_date" in update_data else None,
            "actual_launch_date": _parse_date(update_data.pop("actual_launch_date", None)) if "actual_launch_date" in update_data else None,
        }

        for key, val in update_data.items():
            if val is not None and hasattr(review, key):
                setattr(review, key, val)

        if field_map.get("review_date") is not None:
            review.review_date = field_map["review_date"]
        if field_map.get("actual_launch_date") is not None:
            review.actual_launch_date = field_map["actual_launch_date"]

        db.commit()
        db.refresh(review)
        return _review_to_dict(review)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新复盘失败: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新复盘失败: {str(e)}")
