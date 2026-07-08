"""ImprovementTask API — 复盘改进任务管理

端点：
- GET    /api/reviews/{review_id}/tasks — 获取复盘关联的改进任务列表
- POST   /api/reviews/{review_id}/tasks — 创建改进任务
- PUT    /api/tasks/{task_id} — 更新任务状态/字段
- GET    /api/reviews — 列出所有复盘（含策划名称/系列）
- GET    /api/reviews/compare — 多复盘对比分析
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlanReview, ProductPlan
from app.models.improvement_task import (
    ImprovementTask, TaskPriority, TaskStatus,
)

router = APIRouter(tags=["复盘改进任务"])


# ── Schemas ──

class TaskCreate(BaseModel):
    """创建改进任务请求"""
    description: str = Field(..., min_length=1, max_length=2000, description="改进任务描述")
    assigned_to: Optional[str] = Field(None, description="负责人用户名")
    priority: str = Field("medium", description="优先级: high/medium/low")
    due_date: Optional[str] = Field(None, description="截止日期 YYYY-MM-DD")


class TaskUpdate(BaseModel):
    """更新改进任务请求"""
    description: Optional[str] = Field(None, max_length=2000)
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None


class TaskOut(BaseModel):
    """改进任务输出"""
    id: str
    review_id: str
    description: str
    assigned_to: Optional[str] = None
    priority: str
    status: str
    due_date: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListOut(BaseModel):
    """改进任务列表输出"""
    items: List[TaskOut]
    total: int


# ── 辅助函数 ──

def _task_to_dict(task: ImprovementTask) -> dict:
    """将 ImprovementTask ORM 转为响应 dict"""
    return {
        "id": task.id,
        "review_id": task.review_id,
        "description": task.description,
        "assigned_to": task.assigned_to,
        "priority": task.priority.value if isinstance(task.priority, TaskPriority) else task.priority,
        "status": task.status.value if isinstance(task.status, TaskStatus) else task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _validate_priority(val: str) -> TaskPriority:
    """校验并返回合法优先级"""
    try:
        return TaskPriority(val)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"无效优先级: {val}，可选值: high/medium/low",
        )


def _validate_status(val: str) -> TaskStatus:
    """校验并返回合法状态"""
    try:
        return TaskStatus(val)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"无效状态: {val}，可选值: open/in_progress/resolved/closed",
        )


def _parse_date(val: Optional[str]) -> Optional[date]:
    """解析日期字符串"""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail=f"无效日期格式: {val}")


def _ensure_review_exists(review_id: str, db: Session) -> None:
    """确认复盘记录存在，不存在则抛 404"""
    review = db.query(ProductPlanReview).filter(ProductPlanReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="复盘记录不存在")


# ── API 端点 ──

@router.get("/reviews/{review_id}/tasks", response_model=TaskListOut)
def list_tasks(
    review_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取复盘关联的改进任务列表"""
    try:
        _ensure_review_exists(review_id, db)
        tasks = (
            db.query(ImprovementTask)
            .filter(ImprovementTask.review_id == review_id)
            .order_by(ImprovementTask.created_at.desc())
            .all()
        )
        return {
            "items": [_task_to_dict(t) for t in tasks],
            "total": len(tasks),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        raise HTTPException(status_code=500, detail=f"查询改进任务列表失败: {str(e)}")


@router.post("/reviews/{review_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(
    review_id: str,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """为复盘创建改进任务"""
    try:
        _ensure_review_exists(review_id, db)

        priority_enum = _validate_priority(data.priority)
        due_date = _parse_date(data.due_date)

        task = ImprovementTask(
            review_id=review_id,
            description=data.description,
            assigned_to=data.assigned_to,
            priority=priority_enum,
            due_date=due_date,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return _task_to_dict(task)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建改进任务失败: {str(e)}")
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建改进任务失败: {str(e)}")


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> None:
    """删除改进任务"""
    try:
        task = db.query(ImprovementTask).filter(ImprovementTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="改进任务不存在")
        db.delete(task)
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除改进任务失败: {str(e)}")


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """更新改进任务（状态、描述、负责人、优先级等）"""
    try:
        task = db.query(ImprovementTask).filter(ImprovementTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="改进任务不存在")

        update_data = data.model_dump(exclude_unset=True)

        # 处理优先级
        if "priority" in update_data and update_data["priority"] is not None:
            task.priority = _validate_priority(update_data["priority"])

        # 处理状态流转
        if "status" in update_data and update_data["status"] is not None:
            new_status = _validate_status(update_data["status"])
            task.status = new_status
            # 如果状态变为 resolved 或 closed，记录解决时间
            if new_status in (TaskStatus.RESOLVED, TaskStatus.CLOSED):
                task.resolved_at = datetime.now()
            elif new_status == TaskStatus.OPEN and task.resolved_at is not None:
                # 重新打开时清除解决时间
                task.resolved_at = None

        # 处理截止日期
        if "due_date" in update_data:
            task.due_date = _parse_date(update_data["due_date"])

        # 处理描述
        if "description" in update_data and update_data["description"] is not None:
            task.description = update_data["description"]

        # 处理负责人
        if "assigned_to" in update_data:
            task.assigned_to = update_data["assigned_to"]

        db.commit()
        db.refresh(task)
        return _task_to_dict(task)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新改进任务失败: {str(e)}")
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新改进任务失败: {str(e)}")


# ── D4-5 复盘对比 Schemas ──


class ReviewListItem(BaseModel):
    """复盘列表条目（含策划名称/系列）"""
    id: str
    plan_id: str
    plan_name: str
    plan_series: Optional[str] = None
    review_date: Optional[str] = None
    rating: Optional[int] = None


class ReviewListOut(BaseModel):
    """复盘列表输出"""
    items: List[ReviewListItem]
    total: int


class ReviewCompareItem(BaseModel):
    """单个复盘的对比数据"""
    review_id: str
    plan_id: str
    plan_name: str
    plan_series: Optional[str] = None
    review_date: Optional[str] = None
    rating: Optional[int] = None
    cost_variance_pct: Optional[float] = None
    schedule_variance_days: Optional[int] = None
    main_issues: Optional[str] = None
    task_total: int = 0
    task_resolved: int = 0
    task_completion_rate: float = 0.0


class ReviewCompareOut(BaseModel):
    """复盘对比输出"""
    items: List[ReviewCompareItem]
    total: int


# ── D4-5 复盘列表 / 对比端点 ──


@router.get("/improvement-tasks", response_model=ReviewListOut)
def list_all_reviews_alias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """(兼容别名) 列出所有复盘 — 等同 /api/reviews"""
    reviews = (
        db.query(ProductPlanReview)
        .join(ProductPlan, ProductPlanReview.product_plan_id == ProductPlan.id)
        .order_by(ProductPlanReview.created_at.desc())
        .all()
    )
    items: list[dict] = []
    for r in reviews:
        plan = r.product_plan
        items.append({
            "id": r.id,
            "plan_id": r.product_plan_id,
            "plan_name": plan.name if plan else "—",
            "plan_series": plan.series if plan and plan.series else None,
            "review_date": str(r.review_date) if r.review_date else None,
            "rating": r.rating,
        })
    return {"items": items, "total": len(items)}


@router.get("/reviews", response_model=ReviewListOut)
def list_all_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """列出所有复盘记录（含策划名称/系列），供对比选择"""
    try:
        reviews = (
            db.query(ProductPlanReview)
            .join(ProductPlan, ProductPlanReview.product_plan_id == ProductPlan.id)
            .order_by(ProductPlanReview.created_at.desc())
            .all()
        )
        items: list[dict] = []
        for r in reviews:
            plan = r.product_plan
            items.append({
                "id": r.id,
                "plan_id": r.product_plan_id,
                "plan_name": plan.name if plan else "—",
                "plan_series": plan.series if plan and plan.series else None,
                "review_date": str(r.review_date) if r.review_date else None,
                "rating": r.rating,
            })
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        raise HTTPException(status_code=500, detail=f"查询复盘列表失败: {str(e)}")


@router.get("/reviews/compare", response_model=ReviewCompareOut)
def compare_reviews(
    review_ids: str = Query(..., description="复盘ID列表，逗号分隔"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """多复盘对比分析

    接收 review_ids 逗号分隔，返回各复盘的对比数据。
    对比字段：评分、成本偏差、进度偏差、主要问题、改进任务完成率。
    """
    try:
        id_list = [rid.strip() for rid in review_ids.split(",") if rid.strip()]
        if len(id_list) < 2:
            raise HTTPException(
                status_code=400,
                detail="至少选择2个复盘进行对比",
            )

        reviews = (
            db.query(ProductPlanReview)
            .filter(ProductPlanReview.id.in_(id_list))
            .all()
        )
        if len(reviews) != len(id_list):
            found_ids = {r.id for r in reviews}
            missing = [rid for rid in id_list if rid not in found_ids]
            raise HTTPException(
                status_code=404,
                detail=f"部分复盘记录不存在: {missing}",
            )

        # 构建结果
        items: list[dict] = []
        for r in reviews:
            plan = r.product_plan
            # 计算改进任务完成率
            task_stats = (
                db.query(
                    func.count(ImprovementTask.id).label("total"),
                    func.sum(
                        func.cast(
                            ImprovementTask.status.in_(["resolved", "closed"]),
                            type_=func.Integer,
                        )
                    ).label("resolved"),
                )
                .filter(ImprovementTask.review_id == r.id)
                .first()
            )
            task_total = task_stats.total if task_stats and task_stats.total else 0
            task_resolved = task_stats.resolved if task_stats and task_stats.resolved else 0
            task_completion_rate = (
                round(task_resolved / task_total * 100, 1) if task_total > 0 else 0.0
            )

            # 合并主要问题（从市场反馈和经验教训提取摘要）
            issues_parts: list[str] = []
            if r.market_feedback:
                issues_parts.append(r.market_feedback[:100])
            if r.lessons_learned:
                issues_parts.append(r.lessons_learned[:100])
            main_issues = "；".join(issues_parts) if issues_parts else None
            if main_issues and len(main_issues) > 200:
                main_issues = main_issues[:200] + "..."

            items.append({
                "review_id": r.id,
                "plan_id": r.product_plan_id,
                "plan_name": plan.name if plan else "—",
                "plan_series": plan.series if plan and plan.series else None,
                "review_date": str(r.review_date) if r.review_date else None,
                "rating": r.rating,
                "cost_variance_pct": r.cost_variance_pct,
                "schedule_variance_days": r.schedule_variance_days,
                "main_issues": main_issues,
                "task_total": task_total,
                "task_resolved": task_resolved,
                "task_completion_rate": task_completion_rate,
            })

        return {"items": items, "total": len(items)}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        raise HTTPException(status_code=500, detail=f"复盘对比查询失败: {str(e)}")
