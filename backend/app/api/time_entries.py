"""任务工时记录 + 资源负载 API — TimeEntry CRUD + 团队负载聚合"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, require_menu
from app.models.user import User
from app.models.project import Task, TimeEntry

router = APIRouter(prefix="/projects/{pid}/time", tags=["任务工时"])


@router.get("")
def list_time_entries(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
):
    """列出项目下所有工时记录"""
    entries = (
        db.query(TimeEntry)
        .join(Task, TimeEntry.task_id == Task.id)
        .filter(Task.project_id == pid)
        .order_by(TimeEntry.entry_date.desc())
        .all()
    )
    return [{
        "id": e.id,
        "task_id": e.task_id,
        "task_title": db.query(Task.title).filter(Task.id == e.task_id).scalar(),
        "user_name": e.user_name,
        "hours": e.hours,
        "entry_date": str(e.entry_date),
        "description": e.description,
    } for e in entries]


@router.post("")
def create_time_entry(
    pid: int,
    task_id: int,
    hours: int,
    entry_date: date,
    user_name: str | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    """记录工时"""
    t = db.query(Task).filter(Task.id == task_id, Task.project_id == pid).first()
    if not t:
        raise HTTPException(404, "任务不存在")
    entry = TimeEntry(task_id=task_id, user_name=user_name, hours=hours, entry_date=entry_date, description=description)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "ok": True}


@router.delete("/{entry_id}")
def delete_time_entry(
    pid: int,
    entry_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager")),
) -> dict:
    """删除工时记录"""
    e = (
        db.query(TimeEntry)
        .join(Task, TimeEntry.task_id == Task.id)
        .filter(TimeEntry.id == entry_id, Task.project_id == pid)
        .first()
    )
    if not e:
        raise HTTPException(404, "记录不存在")
    db.delete(e)
    db.commit()
    return {"ok": True}


# ── 资源负载 ──


@router.get("/workload")
def workload_summary(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
):
    """团队成员资源负载概览"""
    # 按负责人聚合任务数
    rows = (
        db.query(Task.assignee, sa_func.count(Task.id), sa_func.sum(TimeEntry.hours))
        .outerjoin(TimeEntry, TimeEntry.task_id == Task.id)
        .filter(Task.project_id == pid, Task.assignee.isnot(None))
        .group_by(Task.assignee)
        .all()
    )
    return [{
        "assignee": r[0],
        "task_count": r[1],
        "total_hours": r[2] or 0,
    } for r in rows]
