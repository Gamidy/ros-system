"""任务依赖管理API — TaskDependency CRUD + 依赖链分析"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, require_menu
from app.models.user import User
from app.models.project import Task, TaskDependency

router = APIRouter(prefix="/projects/{pid}/tasks", tags=["任务依赖管理"])


@router.get("/dependencies")
def list_dependencies(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
):
    """列出任务所有依赖关系"""
    # 确认项目存在
    deps = (
        db.query(TaskDependency)
        .join(Task, TaskDependency.task_id == Task.id)
        .filter(Task.project_id == pid)
        .all()
    )
    result = []
    for d in deps:
        task = db.query(Task).filter(Task.id == d.task_id).first()
        dep_task = db.query(Task).filter(Task.id == d.depends_on_task_id).first()
        result.append({
            "id": d.id,
            "task_id": d.task_id,
            "task_title": task.title if task else None,
            "depends_on_task_id": d.depends_on_task_id,
            "depends_on_title": dep_task.title if dep_task else None,
            "dep_type": d.dep_type,
            "lag_days": d.lag_days,
        })
    return result


@router.post("/dependencies")
def create_dependency(
    pid: int,
    task_id: int,
    depends_on_task_id: int,
    dep_type: str = "finish_to_start",
    lag_days: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    """创建任务依赖"""
    # 验证两个任务都属于同一个项目
    t1 = db.query(Task).filter(Task.id == task_id, Task.project_id == pid).first()
    t2 = db.query(Task).filter(Task.id == depends_on_task_id, Task.project_id == pid).first()
    if not t1 or not t2:
        raise HTTPException(404, "任务不存在")
    if task_id == depends_on_task_id:
        raise HTTPException(400, "任务不能依赖自己")
    if dep_type not in ("finish_to_start", "start_to_start", "finish_to_finish"):
        raise HTTPException(400, "无效依赖类型")

    # 检查是否已存在
    existing = db.query(TaskDependency).filter(
        TaskDependency.task_id == task_id,
        TaskDependency.depends_on_task_id == depends_on_task_id,
    ).first()
    if existing:
        raise HTTPException(400, "依赖关系已存在")

    dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id, dep_type=dep_type, lag_days=lag_days)
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return {"id": dep.id, "ok": True}


@router.delete("/dependencies/{dep_id}")
def delete_dependency(
    pid: int,
    dep_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    """删除依赖关系"""
    dep = (
        db.query(TaskDependency)
        .join(Task, TaskDependency.task_id == Task.id)
        .filter(TaskDependency.id == dep_id, Task.project_id == pid)
        .first()
    )
    if not dep:
        raise HTTPException(404, "依赖关系不存在")
    db.delete(dep)
    db.commit()
    return {"ok": True}
