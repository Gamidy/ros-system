"""实验执行 API — Phase 6 S1"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.test_execution import TestExecution
from app.schemas import (
    TestExecutionCreate, TestExecutionOut,
)

router = APIRouter(prefix="/test-executions", tags=["实验执行"])


@router.post("", response_model=TestExecutionOut)
def create_test_execution(
    data: TestExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("test-executions")),
) -> TestExecutionOut:
    execution = TestExecution(
        **data.model_dump(),
        status="running",
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


@router.patch("/{eid}/complete", response_model=TestExecutionOut)
def complete_test_execution(
    eid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("test-executions")),
) -> TestExecutionOut:
    """完成执行：设置 end_time，自动计算 duration"""
    execution = db.query(TestExecution).filter(TestExecution.id == eid).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    now = datetime.now(timezone.utc)
    execution.end_time = now
    if execution.start_time:
        delta = now - execution.start_time
        execution.duration_minutes = int(delta.total_seconds() // 60)
    execution.status = "completed"
    execution.updated_at = now
    db.commit()
    db.refresh(execution)
    return execution


@router.get("", response_model=list[TestExecutionOut])
def list_test_executions(
    test_request_id: int = Query(None, description="实验申请ID"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("test-executions")),
) -> list[TestExecutionOut]:
    q = db.query(TestExecution)
    if test_request_id is not None:
        q = q.filter(TestExecution.test_request_id == test_request_id)
    return q.order_by(TestExecution.created_at.desc()).all()


@router.delete("/{eid}")
def delete_test_execution(
    eid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("test-executions")),
) -> dict:
    execution = db.query(TestExecution).filter(TestExecution.id == eid).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    db.delete(execution)
    db.commit()
    return {"ok": True, "message": "执行记录已删除"}


@router.patch("/{eid}/complete")
def complete_test_execution(
    eid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("test-executions")),
) -> dict:
    """标记执行完成"""
    execution = db.query(TestExecution).filter(TestExecution.id == eid).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    execution.status = "completed"
    execution.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "completed"}


@router.patch("/{eid}/abort")
def abort_test_execution(
    eid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("test-executions")),
) -> dict:
    """终止执行"""
    execution = db.query(TestExecution).filter(TestExecution.id == eid).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    execution.status = "aborted"
    db.commit()
    return {"ok": True, "status": "aborted"}
