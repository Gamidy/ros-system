"""产品经理(PM)工作台API — 聚合视图 + 提案列表（核心Crud）

子模块:
  - pm_workspace_drafts.py    草稿 CRUD + 提交/退回
  - pm_workspace_planning.py  年度规划 CRUD
  - pm_workspace_config.py    配置端点
  - pm_workspace_utils.py     共享辅助函数
"""
from datetime import datetime, date
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.project import Project, Program
from app.models.product import Product
from app.models.annual_plan import AnnualPlan
from app.api.pm_workspace_utils import _project_to_dict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pm", tags=["产品经理工作台"])


def _require_pm(current_user: User = Depends(get_current_user)) -> User:
    """校验当前用户为产品经理或超级管理员"""
    return require_role("product_manager")(current_user)


@router.get("/programs")
def list_active_programs(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> list:
    """返回所有活跃项目群，供立项时选择"""
    programs = db.query(Program).filter(Program.status == "active").all()
    return [{"id": p.id, "name": p.name, "code": p.code} for p in programs]


@router.get("/workspace")
def pm_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """返回 PM 工作台聚合数据"""
    owner_name = current_user.username
    my_projects_query = db.query(Project).filter(Project.owner == owner_name)
    my_projects_raw = my_projects_query.order_by(Project.created_at.desc()).all()

    my_projects = []
    total_budget = 0
    completed_count = 0
    overdue_count = 0
    today = date.today()

    for p in my_projects_raw:
        my_projects.append(_project_to_dict(p))
        if p.budget:
            total_budget += p.budget
        if p.status == "completed":
            completed_count += 1
        if p.status not in ("completed", "cancelled") and p.target_end_date and p.target_end_date < today:
            overdue_count += 1

    products_raw = db.query(Product).order_by(Product.created_at.desc()).all()
    products = [{"id": prod.id, "code": prod.code, "name": prod.name, "status": prod.status,
                 "capacity": prod.capacity, "platform_id": prod.platform_id} for prod in products_raw]

    total_projects = len(my_projects_raw)
    active_projects = sum(1 for p in my_projects_raw if p.status not in ("completed", "cancelled"))
    stats = {"total_projects": total_projects, "active_projects": active_projects,
             "total_budget": total_budget, "completed_count": completed_count, "overdue_count": overdue_count}

    annual_plans_raw = db.query(AnnualPlan).order_by(AnnualPlan.year.desc(), AnnualPlan.created_at.desc()).all()
    planning_items = []
    for ap in annual_plans_raw:
        project_count = 0
        planning_items.append({"id": ap.id, "name": ap.name, "year": ap.year,
            "description": ap.description, "doc_ref": ap.doc_ref, "owner": ap.owner,
            "project_count": project_count,
            "created_at": str(ap.created_at) if ap.created_at else None,
            "updated_at": str(ap.updated_at) if ap.updated_at else None})

    recent_projects = my_projects[:5] if len(my_projects) > 5 else my_projects

    return {"my_projects": my_projects, "products": products, "stats": stats,
            "planning_items": planning_items, "recent_projects": recent_projects}


@router.get("/proposals")
def list_my_proposals(
    status: str = Query("all", description="过滤状态: draft(草稿) / submitted(已提交) / all(全部)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """返回当前用户的所有提案（含草稿和已提交）"""
    owner_name = current_user.username
    query = db.query(Project).filter(Project.owner == owner_name, Project.is_deleted == False)
    if status == "draft":
        query = query.filter(Project.is_draft == True)
    elif status == "submitted":
        query = query.filter(Project.is_draft == False)
    proposals_raw = query.order_by(Project.updated_at.desc()).all()
    proposals = [_project_to_dict(p) for p in proposals_raw]
    return {"proposals": proposals, "total": len(proposals),
            "draft_count": sum(1 for p in proposals_raw if p.is_draft),
            "submitted_count": sum(1 for p in proposals_raw if not p.is_draft)}


@router.get("/proposals/{proposal_id}")
def get_proposal_detail(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """获取单个提案详情"""
    from app.models.project import Project
    proposal = db.query(Project).filter(Project.id == proposal_id, Project.is_deleted == False).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="提案不存在")
    return _project_to_dict(proposal)
