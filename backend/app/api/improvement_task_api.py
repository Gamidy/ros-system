"""ImprovementTask API — 复盘改进任务管理

端点：
- GET    /api/reviews/{review_id}/tasks — 获取复盘关联的改进任务列表
- POST   /api/reviews/{review_id}/tasks — 创建改进任务
- PUT    /api/tasks/{task_id} — 更新任务状态/字段
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlanReview
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

@router.get("/api/reviews/{review_id}/tasks", response_model=TaskListOut)
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
        raise HTTPException(status_code=500, detail=f"查询改进任务列表失败: {str(e)}")


@router.post("/api/reviews/{review_id}/tasks", response_model=TaskOut, status_code=201)
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
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建改进任务失败: {str(e)}")


@router.put("/api/tasks/{task_id}", response_model=TaskOut)
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
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新改进任务失败: {str(e)}")
