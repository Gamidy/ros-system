"""任务评论 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.project import Task, TaskComment

router = APIRouter(prefix="/projects/{pid}/tasks", tags=["任务评论"])


@router.get("/{tid}/comments")
def list_comments(pid: int, tid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    t = db.query(Task).filter(Task.id == tid, Task.project_id == pid).first()
    if not t:
        raise HTTPException(404)
    comments = db.query(TaskComment).filter(TaskComment.task_id == tid).order_by(TaskComment.created_at).all()
    return [{"id": c.id, "author": c.author, "content": c.content, "created_at": str(c.created_at)} for c in comments]


@router.post("/{tid}/comments")
def create_comment(pid: int, tid: int, content: str, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user), _=Depends(require_menu("projects"))):
    t = db.query(Task).filter(Task.id == tid, Task.project_id == pid).first()
    if not t:
        raise HTTPException(404)
    c = TaskComment(task_id=tid, author=current_user.real_name or current_user.username, content=content)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "ok": True}
