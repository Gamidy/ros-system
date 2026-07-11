from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.models import Project, ProjectTask, User
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectTaskCreate, ProjectTaskResponse
)

router = APIRouter(prefix="/api/v1/projects", tags=["项目管理"])

def generate_project_code(db: Session, tenant_id: UUID) -> str:
    """生成项目编号 PRJ-YYYY-XXXXX"""
    year = datetime.now().year
    prefix = f"PRJ-{year}-"
    
    latest = db.query(Project).filter(
        Project.tenant_id == tenant_id,
        Project.project_code.like(f"{prefix}%")
    ).order_by(Project.project_code.desc()).first()
    
    if latest:
        seq = int(latest.project_code.split("-")[-1]) + 1
    else:
        seq = 1
    
    return f"{prefix}{seq:05d}"

@router.get("")
async def list_projects(
    tenant_id: UUID,
    status: Optional[str] = None,
    project_type: Optional[str] = None,
    manager_id: Optional[UUID] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目列表"""
    query = db.query(Project).filter(Project.tenant_id == tenant_id)
    
    if status:
        query = query.filter(Project.status == status)
    if project_type:
        query = query.filter(Project.project_type == project_type)
    if manager_id:
        query = query.filter(Project.manager_id == manager_id)
    if keyword:
        query = query.filter(
            func.lower(Project.project_name).contains(keyword.lower()) |
            func.lower(Project.project_code).contains(keyword.lower())
        )
    
    total = query.count()
    projects = query.order_by(Project.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    result = []
    for project in projects:
        data = {
            "id": project.id,
            "tenant_id": project.tenant_id,
            "project_code": project.project_code,
            "project_name": project.project_name,
            "description": project.description,
            "project_type": project.project_type,
            "status": project.status,
            "priority": project.priority,
            "manager_id": project.manager_id,
            "manager_name": project.manager.full_name if project.manager else None,
            "start_date": str(project.start_date) if project.start_date else None,
            "target_end_date": str(project.target_end_date) if project.target_end_date else None,
            "actual_end_date": str(project.actual_end_date) if project.actual_end_date else None,
            "budget": float(project.budget) if project.budget else None,
            "progress": float(project.progress),
            "created_by": project.created_by,
            "creator_name": project.creator.full_name if hasattr(project, 'creator') and project.creator else None,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }
        result.append(data)
    
    return {"total": total, "items": result, "page": page, "page_size": page_size}

@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project.create"))
):
    """创建项目"""
    project_code = generate_project_code(db, data.tenant_id)
    
    project = Project(
        tenant_id=data.tenant_id,
        project_code=project_code,
        project_name=data.project_name,
        description=data.description,
        project_type=data.project_type,
        priority=data.priority,
        manager_id=data.manager_id,
        start_date=data.start_date,
        target_end_date=data.target_end_date,
        budget=data.budget,
        created_by=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        project_code=project.project_code,
        project_name=project.project_name,
        description=project.description,
        project_type=project.project_type,
        status=project.status,
        priority=project.priority,
        manager_id=project.manager_id,
        manager_name=project.manager.full_name if project.manager else None,
        start_date=str(project.start_date) if project.start_date else None,
        target_end_date=str(project.target_end_date) if project.target_end_date else None,
        actual_end_date=str(project.actual_end_date) if project.actual_end_date else None,
        budget=float(project.budget) if project.budget else None,
        progress=float(project.progress),
        created_by=project.created_by,
        creator_name=current_user.full_name,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return ProjectResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        project_code=project.project_code,
        project_name=project.project_name,
        description=project.description,
        project_type=project.project_type,
        status=project.status,
        priority=project.priority,
        manager_id=project.manager_id,
        manager_name=project.manager.full_name if project.manager else None,
        start_date=str(project.start_date) if project.start_date else None,
        target_end_date=str(project.target_end_date) if project.target_end_date else None,
        actual_end_date=str(project.actual_end_date) if project.actual_end_date else None,
        budget=float(project.budget) if project.budget else None,
        progress=float(project.progress),
        created_by=project.created_by,
        creator_name=project.creator.full_name if hasattr(project, 'creator') and project.creator else None,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project.edit"))
):
    """更新项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    project.updated_by = current_user.id
    db.commit()
    db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        tenant_id=project.tenant_id,
        project_code=project.project_code,
        project_name=project.project_name,
        description=project.description,
        project_type=project.project_type,
        status=project.status,
        priority=project.priority,
        manager_id=project.manager_id,
        manager_name=project.manager.full_name if project.manager else None,
        start_date=str(project.start_date) if project.start_date else None,
        target_end_date=str(project.target_end_date) if project.target_end_date else None,
        actual_end_date=str(project.actual_end_date) if project.actual_end_date else None,
        budget=float(project.budget) if project.budget else None,
        progress=float(project.progress),
        created_by=project.created_by,
        creator_name=project.creator.full_name if hasattr(project, 'creator') and project.creator else None,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project.edit"))
):
    """删除项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    db.delete(project)
    db.commit()
    
    return {"message": "项目已删除"}

# ==================== 项目任务 ====================

@router.get("/{project_id}/tasks")
async def list_project_tasks(
    project_id: UUID,
    parent_id: Optional[UUID] = None,
    status: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取项目任务列表"""
    query = db.query(ProjectTask).filter(ProjectTask.project_id == project_id)
    
    if parent_id:
        query = query.filter(ProjectTask.parent_id == parent_id)
    else:
        query = query.filter(ProjectTask.parent_id.is_(None))
    if status:
        query = query.filter(ProjectTask.status == status)
    if assigned_to:
        query = query.filter(ProjectTask.assigned_to == assigned_to)
    
    tasks = query.order_by(ProjectTask.sort_order).all()
    
    result = []
    for task in tasks:
        data = {
            "id": task.id,
            "project_id": task.project_id,
            "parent_id": task.parent_id,
            "task_code": task.task_code,
            "task_name": task.task_name,
            "description": task.description,
            "task_type": task.task_type,
            "status": task.status,
            "priority": task.priority,
            "assigned_to": task.assigned_to,
            "assignee_name": task.assignee.full_name if task.assignee else None,
            "planned_start": str(task.planned_start) if task.planned_start else None,
            "planned_end": str(task.planned_end) if task.planned_end else None,
            "actual_start": str(task.actual_start) if task.actual_start else None,
            "actual_end": str(task.actual_end) if task.actual_end else None,
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours else None,
            "progress": float(task.progress),
            "sort_order": task.sort_order,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        result.append(data)
    
    return result

@router.post("/{project_id}/tasks", response_model=ProjectTaskResponse)
async def create_project_task(
    project_id: UUID,
    data: ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project.edit"))
):
    """创建项目任务"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    task = ProjectTask(
        project_id=project_id,
        parent_id=data.parent_id,
        task_name=data.task_name,
        description=data.description,
        task_type=data.task_type,
        priority=data.priority,
        assigned_to=data.assigned_to,
        planned_start=data.planned_start,
        planned_end=data.planned_end,
        estimated_hours=data.estimated_hours,
        created_by=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return ProjectTaskResponse(
        id=task.id,
        project_id=task.project_id,
        parent_id=task.parent_id,
        task_code=task.task_code,
        task_name=task.task_name,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        assignee_name=task.assignee.full_name if task.assignee else None,
        planned_start=str(task.planned_start) if task.planned_start else None,
        planned_end=str(task.planned_end) if task.planned_end else None,
        actual_start=str(task.actual_start) if task.actual_start else None,
        actual_end=str(task.actual_end) if task.actual_end else None,
        estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
        actual_hours=float(task.actual_hours) if task.actual_hours else None,
        progress=float(task.progress),
        created_at=task.created_at
    )

@router.put("/{project_id}/tasks/{task_id}", response_model=ProjectTaskResponse)
async def update_project_task(
    project_id: UUID,
    task_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project.edit"))
):
    """更新项目任务"""
    task = db.query(ProjectTask).filter(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 更新任务状态
    if "status" in data:
        task.status = data["status"]
        if data["status"] == "in_progress" and not task.actual_start:
            task.actual_start = datetime.now().date()
        if data["status"] == "completed" and not task.actual_end:
            task.actual_end = datetime.now().date()
    
    if "progress" in data:
        task.progress = data["progress"]
    
    if "assigned_to" in data:
        task.assigned_to = data["assigned_to"]
    
    if "actual_hours" in data:
        task.actual_hours = data["actual_hours"]
    
    task.updated_by = current_user.id
    db.commit()
    db.refresh(task)
    
    # 更新项目进度
    update_project_progress(db, project_id)
    
    return ProjectTaskResponse(
        id=task.id,
        project_id=task.project_id,
        parent_id=task.parent_id,
        task_code=task.task_code,
        task_name=task.task_name,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        priority=task.priority,
        assigned_to=task.assigned_to,
        assignee_name=task.assignee.full_name if task.assignee else None,
        planned_start=str(task.planned_start) if task.planned_start else None,
        planned_end=str(task.planned_end) if task.planned_end else None,
        actual_start=str(task.actual_start) if task.actual_start else None,
        actual_end=str(task.actual_end) if task.actual_end else None,
        estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
        actual_hours=float(task.actual_hours) if task.actual_hours else None,
        progress=float(task.progress),
        created_at=task.created_at
    )

def update_project_progress(db: Session, project_id: UUID):
    """更新项目进度"""
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    if not tasks:
        return
    
    total_progress = sum(float(task.progress) for task in tasks)
    avg_progress = total_progress / len(tasks)
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        project.progress = avg_progress
        db.commit()

@router.delete("/{project_id}/tasks/{task_id}")
async def delete_project_task(
    project_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project.edit"))
):
    """删除项目任务"""
    task = db.query(ProjectTask).filter(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    db.delete(task)
    db.commit()
    
    # 更新项目进度
    update_project_progress(db, project_id)
    
    return {"message": "任务已删除"}
