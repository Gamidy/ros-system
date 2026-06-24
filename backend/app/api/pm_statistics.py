"""PM 工作台统计聚合端点

提供产品策划模块的顶级统计数据：
- 年度规划数、项目总数、总预算、完成率、逾期率
"""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.annual_plan import AnnualPlan
from app.api.pm_workspace import _require_pm

router = APIRouter(prefix="/pm", tags=["产品经理工作台-统计"])


@router.get("/statistics")
def pm_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """返回 PM 工作台统计聚合数据"""
    owner_name = current_user.username
    today = date.today()

    # 年度规划总数
    annual_plan_count = db.query(sqlfunc.count(AnnualPlan.id)).scalar() or 0

    # 当前用户的项目统计
    my_projects_query = db.query(Project).filter(Project.owner == owner_name, Project.is_deleted == False)
    total_projects = my_projects_query.count()

    # 预算总和（排除草稿）
    budget_result = db.query(sqlfunc.coalesce(sqlfunc.sum(Project.budget), 0)).filter(
        Project.owner == owner_name,
        Project.is_deleted == False,
        Project.is_draft == False,
    ).scalar()
    total_budget = float(budget_result or 0)

    # 完成计数
    completed_count = my_projects_query.filter(Project.status == "completed").count()

    # 逾期计数（未完成且 target_end_date < today）
    overdue_count = my_projects_query.filter(
        Project.status.not_in(["completed", "cancelled"]),
        Project.target_end_date != None,
        Project.target_end_date < today,
    ).count()

    # 进行中计数（排除 completed/cancelled）
    running_count = my_projects_query.filter(
        Project.status.not_in(["completed", "cancelled", "planning"])
    ).count()

    # 计算率值
    completed_projects = max(total_projects, 1)  # 防止除零
    completion_rate = round((completed_count / completed_projects) * 100, 1)
    overdue_rate = round((overdue_count / completed_projects) * 100, 1)

    return {
        "annual_plan_count": annual_plan_count,
        "total_projects": total_projects,
        "total_budget": total_budget,
        "completion_rate": completion_rate,
        "overdue_rate": overdue_rate,
        "running_count": running_count,
        "overdue_count": overdue_count,
        "completed_count": completed_count,
    }
