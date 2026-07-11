"""项目/WBS/任务/Gate API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.database import get_db
from app.core.security import get_current_user
from app.crud.project import project_crud, wbs_crud, task_crud, gate_crud, can_transition
from app.schemas.project import (
    ProjectCreate, ProjectRead, WBSCreate, WBSRead,
    TaskCreate, TaskRead, GateDecisionInput, GateRead,
)
from app.models.project import Gate, PhaseEnum, Task

project_router = APIRouter(prefix="/projects", tags=["项目管理"])
wbs_router = APIRouter(prefix="/wbs", tags=["WBS"])
task_router = APIRouter(prefix="/tasks", tags=["任务卡"])


# ── Projects ──
@project_router.get("", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await project_crud.get_multi(db)


@project_router.post("", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj_in = data.model_dump()
    obj_in["current_phase"] = PhaseEnum.NPR
    return await project_crud.create(db, obj_in=obj_in)


@project_router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await project_crud.get(db, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="项目不存在")
    return obj


@project_router.put("/{project_id}/phase")
async def advance_phase(project_id: int, target_phase: str, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await project_crud.get(db, project_id)
    if not obj:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not can_transition(obj.current_phase, target_phase):
        raise HTTPException(status_code=400, detail=f"不允许从 {obj.current_phase} 转到 {target_phase}")
    obj.current_phase = target_phase
    await db.flush()
    return {"message": f"阶段切换成功: {target_phase}"}


# ── Gates ──
@project_router.get("/{project_id}/gates", response_model=list[GateRead])
async def get_project_gates(project_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await gate_crud.get_by_project(db, project_id=project_id)


@project_router.post("/{project_id}/gates/{phase}/decide", response_model=GateRead, status_code=201)
async def decide_gate(
    project_id: int, phase: str, data: GateDecisionInput,
    db: AsyncSession = Depends(get_db), user=Depends(get_current_user),
):
    gate = Gate(
        project_id=project_id, phase=phase, decision=data.decision,
        comment=data.comment, decided_by_id=user.id,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(gate)
    await db.flush()
    await db.refresh(gate)
    return gate


# ── WBS ──
@wbs_router.get("", response_model=list[WBSRead])
async def list_wbs(project_id: int = Query(...), db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await wbs_crud.get_tree(db, project_id=project_id)


@wbs_router.post("", response_model=WBSRead, status_code=201)
async def create_wbs(data: WBSCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await wbs_crud.create(db, obj_in=data.model_dump())


# ── Tasks ──
@task_router.get("", response_model=list[TaskRead])
async def list_tasks(wbs_id: int = Query(...), db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.wbs_id == wbs_id))
    return list(result.scalars().all())


@task_router.post("", response_model=TaskRead, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await task_crud.create(db, obj_in=data.model_dump())
