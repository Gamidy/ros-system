"""ProductPlan Review API — P4复盘

3个端点：
- POST /product-plans/{plan_id}/review — 提交复盘
- GET  /product-plans/{plan_id}/review — 查看复盘
- PUT  /product-plans/{plan_id}/review — 更新复盘

Added in D4-2:
- GET  /product-plans/{plan_id}/auto-variance — 获取自动计算的偏差值
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import (
    ProductPlan, ProductPlanReview, ProductPlanProjectLink,
    Cost, CostType,
)
from app.models.project import Project
from app.models.product_plan_subs import ProductPlanInitiation

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
    manual_override: Optional[bool] = False


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
    manual_override: Optional[bool] = None


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
    # D4-2: 自动计算标识
    cost_variance_pct_auto: Optional[float] = None
    schedule_variance_days_auto: Optional[int] = None
    cost_variance_source: str = "manual"
    schedule_variance_source: str = "manual"

    class Config:
        from_attributes = True


class AutoVarianceOut(BaseModel):
    """自动计算的偏差值"""
    cost_variance_pct: Optional[float] = None
    schedule_variance_days: Optional[int] = None
    has_project_data: bool = False
    target_cost_total: Optional[float] = None
    actual_cost_total: Optional[float] = None
    planned_launch_date: Optional[str] = None
    actual_launch_date: Optional[str] = None


# ── 辅助函数 ──

def _calc_cost_metrics(plan_id: str, db: Session) -> dict:
    """计算成本偏差指标（子函数，≤50行）
    
    从 Cost 表和关联项目计算目标/实际成本及偏差百分比。
    """
    # 1. 计算目标成本总计
    target_cost_total = (
        db.query(func.sum(Cost.target_value))
        .filter(
            Cost.product_plan_id == plan_id,
            Cost.cost_type == CostType.TARGET,
        )
        .scalar()
    ) or 0.0
    target_cost_total = float(target_cost_total)

    # 2. 计算实际成本总计
    actual_cost_total = (
        db.query(func.sum(Cost.actual_value))
        .filter(
            Cost.product_plan_id == plan_id,
            Cost.cost_type == CostType.ACTUAL,
        )
        .scalar()
    ) or 0.0
    actual_cost_total = float(actual_cost_total)

    # 3. 如果 Cost 表没有 actual 数据，尝试从关联项目获取
    if actual_cost_total == 0.0:
        links = (
            db.query(ProductPlanProjectLink)
            .filter(
                ProductPlanProjectLink.product_plan_id == plan_id,
                ProductPlanProjectLink.link_type.in_(["primary", "alternative", None]),
            )
            .all()
        )
        if links:
            project_ids = [link.project_id for link in links]
            project_actual = (
                db.query(func.sum(Project.budget))
                .filter(Project.id.in_(project_ids))
                .scalar()
            ) or 0.0
            actual_cost_total = float(project_actual)

    # 4. 计算成本偏差
    cost_variance_pct: Optional[float] = None
    if target_cost_total > 0 and actual_cost_total > 0:
        cost_variance_pct = round(
            (actual_cost_total - target_cost_total) / target_cost_total * 100, 2
        )

    return {
        "cost_variance_pct": cost_variance_pct,
        "target_cost_total": target_cost_total,
        "actual_cost_total": actual_cost_total,
    }


def _calc_schedule_metrics(plan_id: str, db: Session) -> dict:
    """计算进度偏差指标（子函数，≤50行）
    
    从 ProductPlanInitiation 获取计划上市日期，
    从关联 Project 获取实际上市日期，计算偏差天数。
    """
    schedule_variance_days: Optional[int] = None
    planned_launch_date_str: Optional[str] = None
    actual_launch_date_str: Optional[str] = None

    # 计划上市日期从 ProductPlanInitiation.required_date 获取
    initiation = (
        db.query(ProductPlanInitiation)
        .filter(ProductPlanInitiation.product_plan_id == plan_id)
        .first()
    )
    if initiation and initiation.required_date:
        planned_launch_date_str = initiation.required_date.isoformat()

    # 实际日期从关联项目获取
    links = (
        db.query(ProductPlanProjectLink)
        .filter(
            ProductPlanProjectLink.product_plan_id == plan_id,
            ProductPlanProjectLink.link_type.in_(["primary", None]),
        )
        .all()
    )
    if links:
        project_ids = [link.project_id for link in links]
        project = (
            db.query(Project)
            .filter(Project.id.in_(project_ids), Project.actual_end_date.isnot(None))
            .order_by(Project.actual_end_date.desc())
            .first()
        )
        if project and project.actual_end_date:
            actual_launch_date_str = project.actual_end_date.isoformat()

    if planned_launch_date_str and actual_launch_date_str:
        try:
            planned = datetime.fromisoformat(planned_launch_date_str).date()
            actual = datetime.fromisoformat(actual_launch_date_str).date()
            schedule_variance_days = (actual - planned).days
        except (ValueError, TypeError):
            pass

    return {
        "schedule_variance_days": schedule_variance_days,
        "planned_launch_date": planned_launch_date_str,
        "actual_launch_date": actual_launch_date_str,
    }


def auto_calculate_variance(plan_id: str, db: Session) -> dict:
    """从关联项目数据自动计算成本和进度偏差
    
    委托给 _calc_cost_metrics 和 _calc_schedule_metrics，
    组合结果并计算 has_project_data 标识。
    """
    cost_metrics = _calc_cost_metrics(plan_id, db)
    schedule_metrics = _calc_schedule_metrics(plan_id, db)

    has_project_data = (
        cost_metrics["target_cost_total"] > 0
        or cost_metrics["actual_cost_total"] > 0
        or schedule_metrics["planned_launch_date"] is not None
    )

    return {
        "cost_variance_pct": cost_metrics["cost_variance_pct"],
        "schedule_variance_days": schedule_metrics["schedule_variance_days"],
        "has_project_data": has_project_data,
        "target_cost_total": cost_metrics["target_cost_total"],
        "actual_cost_total": cost_metrics["actual_cost_total"],
        "planned_launch_date": schedule_metrics["planned_launch_date"],
        "actual_launch_date": schedule_metrics["actual_launch_date"],
    }


def _review_to_dict(review: ProductPlanReview, auto_variance: Optional[dict] = None) -> dict:
    """将 ProductPlanReview ORM 转为响应 dict
    
    Args:
        review: ProductPlanReview ORM 对象
        auto_variance: 可选，自动计算的偏差值（来自 auto_calculate_variance）
    """
    result = {
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
        # D4-2: 自动计算偏差标识
        "cost_variance_pct_auto": None,
        "schedule_variance_days_auto": None,
        "cost_variance_source": "manual",
        "schedule_variance_source": "manual",
    }

    # 如果提供了自动计算数据，填充字段
    if auto_variance:
        result["cost_variance_pct_auto"] = auto_variance.get("cost_variance_pct")
        result["schedule_variance_days_auto"] = auto_variance.get("schedule_variance_days")
        # 只有手动覆盖关闭且数据库值为空时，才标记为自动
        # 手动覆盖关闭 = 用户没有手动设置值
        if review.cost_variance_pct is None and auto_variance.get("cost_variance_pct") is not None:
            result["cost_variance_pct"] = auto_variance["cost_variance_pct"]
            result["cost_variance_source"] = "auto"
        if review.schedule_variance_days is None and auto_variance.get("schedule_variance_days") is not None:
            result["schedule_variance_days"] = auto_variance["schedule_variance_days"]
            result["schedule_variance_source"] = "auto"

    return result


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
    """提交复盘 — 每个策划最多一条复盘记录，自动计算偏差（无手动覆盖时）"""
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        existing = db.query(ProductPlanReview).filter(
            ProductPlanReview.product_plan_id == plan_id
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="该策划已有复盘记录，请使用 PUT 更新")

        # D4-2: 如果用户没有手动覆盖偏差值，自动计算
        auto_variance = auto_calculate_variance(plan_id, db)
        cost_variance_pct = data.cost_variance_pct
        schedule_variance_days = data.schedule_variance_days
        if not data.manual_override:
            if cost_variance_pct is None and auto_variance["cost_variance_pct"] is not None:
                cost_variance_pct = auto_variance["cost_variance_pct"]
            if schedule_variance_days is None and auto_variance["schedule_variance_days"] is not None:
                schedule_variance_days = auto_variance["schedule_variance_days"]

        review = ProductPlanReview(
            product_plan_id=plan_id,
            review_date=_parse_datetime(data.review_date) or datetime.now(),
            actual_cost_total=data.actual_cost_total,
            cost_variance_pct=cost_variance_pct,
            actual_launch_date=_parse_date(data.actual_launch_date),
            schedule_variance_days=schedule_variance_days,
            market_feedback=data.market_feedback,
            lessons_learned=data.lessons_learned,
            rating=data.rating,
            reviewer_id=data.reviewer_id or current_user.username,
            review_template_id=data.review_template_id,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return _review_to_dict(review, auto_variance)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建复盘失败: {str(e)}")
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建复盘失败: {str(e)}")


@router.get("/{plan_id}/review", response_model=ReviewOut)
def get_review(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """查看策划复盘记录（含自动计算偏差值）"""
    try:
        review = db.query(ProductPlanReview).filter(
            ProductPlanReview.product_plan_id == plan_id
        ).first()
        if not review:
            raise HTTPException(status_code=404, detail="复盘记录不存在")

        # D4-2: 获取自动计算的偏差值用于前端展示
        auto_variance = auto_calculate_variance(plan_id, db)
        return _review_to_dict(review, auto_variance)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        raise HTTPException(status_code=500, detail=f"查询复盘失败: {str(e)}")


@router.put("/{plan_id}/review", response_model=ReviewOut)
def update_review(
    plan_id: str,
    data: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """更新复盘记录（D4-2: 支持手动覆盖模式）"""
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

        # D4-2: 处理手动覆盖
        manual_override = update_data.pop("manual_override", None)

        for key, val in update_data.items():
            if val is not None and hasattr(review, key):
                setattr(review, key, val)

        if field_map.get("review_date") is not None:
            review.review_date = field_map["review_date"]
        if field_map.get("actual_launch_date") is not None:
            review.actual_launch_date = field_map["actual_launch_date"]

        db.commit()
        db.refresh(review)

        # D4-2: 获取自动计算值用于响应
        auto_variance = auto_calculate_variance(plan_id, db)
        return _review_to_dict(review, auto_variance)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新复盘失败: {str(e)}")
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新复盘失败: {str(e)}")


# ── D4-2: 自动计算偏差端点 ──

@router.get("/{plan_id}/auto-variance", response_model=AutoVarianceOut)
def get_auto_variance(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取从项目数据自动计算的偏差值（独立端点，供前端只读展示）"""
    try:
        return auto_calculate_variance(plan_id, db)
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        raise HTTPException(status_code=500, detail=f"自动计算偏差失败: {str(e)}")
