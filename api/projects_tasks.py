"""项目管理API — 任务 & 里程碑管理"""
from datetime import date
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, require_menu, get_current_user
from app.models.user import User
from app.models.project import Project, Task, Milestone
from app.schemas import TaskCreate, MilestoneCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["项目管理-任务"])


# ══════════════════════════════════════════════════════════════
# Task Management
# ══════════════════════════════════════════════════════════════

@router.get("/{pid}/tasks")
def list_tasks(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> list:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return db.query(Task).filter(Task.project_id == pid).order_by(Task.created_at.desc()).all()


@router.post("/{pid}/tasks")
def create_task(
    pid: int, req: TaskCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if req.milestone_id and not db.query(Milestone).filter(Milestone.id == req.milestone_id, Milestone.project_id == pid).first():
        raise HTTPException(status_code=400, detail="里程碑不存在或不属于该项目")
    if req.priority not in ("low", "medium", "high", "urgent"):
        raise HTTPException(status_code=400, detail="无效优先级")
    t = Task(project_id=pid, title=req.title, assignee=req.assignee,
             milestone_id=req.milestone_id, priority=req.priority,
             planned_date=req.planned_date, due_date=req.due_date, description=req.description)
    db.add(t); db.commit(); db.refresh(t)
    return t


@router.patch("/{pid}/tasks/{tid}")
def update_task(
    pid: int, tid: int,
    status: str | None = None, assignee: str | None = None,
    priority: str | None = None, parent_task_id: int | None = None,
    due_date: date | None = None, description: str | None = None,
    sort_order: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    t = db.query(Task).filter(Task.id == tid, Task.project_id == pid).first()
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    if status:
        if status not in ("todo", "in_progress", "done", "blocked"):
            raise HTTPException(status_code=400, detail="无效状态")
        t.status = status
        if status == "done":
            t.actual_date = date.today()
    if assignee is not None:
        t.assignee = assignee
    if priority:
        if priority not in ("low", "medium", "high", "urgent"):
            raise HTTPException(status_code=400, detail="无效优先级")
        t.priority = priority
    if parent_task_id is not None:
        if parent_task_id == tid:
            raise HTTPException(status_code=400, detail="任务不能是自己的父任务")
        t.parent_task_id = parent_task_id
    if due_date is not None:
        t.due_date = due_date
    if description is not None:
        t.description = description
    if sort_order is not None:
        t.sort_order = sort_order
    db.commit(); db.refresh(t)
    return t


@router.delete("/{pid}/tasks/{tid}")
def delete_task(
    pid: int, tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    """删除任务（级联删除子任务）"""
    t = db.query(Task).filter(Task.id == tid, Task.project_id == pid).first()
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    def _cascade_delete(parent_id: int):
        children = db.query(Task).filter(Task.parent_task_id == parent_id).all()
        for c in children:
            _cascade_delete(c.id); db.delete(c)
    _cascade_delete(tid)
    db.delete(t); db.commit()
    return {"ok": True}


@router.get("/{pid}/tasks/tree")
def task_tree(
    pid: int, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("projects")),
) -> dict:
    """返回任务WBS树 (层级结构)"""
    tasks = db.query(Task).filter(Task.project_id == pid).order_by(Task.sort_order, Task.created_at).all()
    task_map: dict[int, dict] = {}
    roots: list[dict] = []
    for t in tasks:
        node = {"id": t.id, "title": t.title, "assignee": t.assignee, "status": t.status,
                "priority": t.priority, "parent_task_id": t.parent_task_id,
                "planned_date": str(t.planned_date) if t.planned_date else None,
                "due_date": str(t.due_date) if t.due_date else None,
                "actual_date": str(t.actual_date) if t.actual_date else None,
                "description": t.description, "sort_order": t.sort_order,
                "milestone_id": t.milestone_id, "children": []}
        task_map[t.id] = node
    for t in tasks:
        node = task_map[t.id]
        if t.parent_task_id and t.parent_task_id in task_map:
            task_map[t.parent_task_id]["children"].append(node)
        else:
            roots.append(node)
    return {"tree": roots, "stats": {"total_tasks": len(tasks), "root_count": len(roots)}}


# ══════════════════════════════════════════════════════════════
# Milestone Management
# ══════════════════════════════════════════════════════════════

@router.get("/{pid}/milestones")
def list_milestones(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> list:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return db.query(Milestone).filter(Milestone.project_id == pid).order_by(Milestone.created_at.desc()).all()


@router.post("/{pid}/milestones")
def create_milestone(
    pid: int, req: MilestoneCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    m = Milestone(project_id=pid, name=req.name, planned_date=req.planned_date,
                  conditions=req.conditions, gate_code=req.gate_code)
    db.add(m); db.commit(); db.refresh(m)
    return m


@router.patch("/{pid}/milestones/{mid}")
def achieve_milestone(
    pid: int, mid: int, status: str = "achieved",
    actual_date: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    m = db.query(Milestone).filter(Milestone.id == mid, Milestone.project_id == pid).first()
    if not m:
        raise HTTPException(status_code=404, detail="里程碑不存在")
    if status == "achieved":
        m.status = "achieved"
        m.actual_date = actual_date or date.today()
        linked_tasks = db.query(Task).filter(Task.milestone_id == mid).all()
        for t in linked_tasks:
            if t.status != "done":
                t.status = "done"; t.actual_date = date.today()
    else:
        m.status = status
    db.commit(); db.refresh(m)
    return {"milestone": m, "auto_completed_tasks": len(db.query(Task).filter(Task.milestone_id == mid).all())}
