"""产品路线图 API — 聚合年度规划 + 项目时间线数据

返回按年度分组的规划与项目甘特图数据，
供前端纯CSS甘特图组件渲染。
"""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.annual_plan import AnnualPlan
from app.api.pm_workspace import _require_pm

router = APIRouter(prefix="/pm", tags=["产品经理工作台-路线图"])


def _project_to_roadmap_item(p: Project) -> dict:
    """将项目转为路线图项目数据"""
    return {
        "id": p.id,
        "name": p.name,
        "status": p.status,
        "start_date": str(p.start_date) if p.start_date else None,
        "target_end_date": str(p.target_end_date) if p.target_end_date else None,
        "actual_end_date": str(p.actual_end_date) if p.actual_end_date else None,
        "budget": p.budget,
        "project_class": p.project_class,
        "annual_planning_ref": p.annual_planning_ref,
    }


@router.get("/roadmap")
def pm_roadmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """返回产品路线图数据：按年份分组的年度规划 + 关联项目列表"""

    # 1. 获取所有年度规划
    plans = db.query(AnnualPlan).order_by(AnnualPlan.year.desc(), AnnualPlan.created_at.desc()).all()

    # 2. 获取所有非草稿项目（含时间线信息）
    projects = db.query(Project).filter(
        Project.is_deleted == False,
        Project.is_draft == False,
    ).order_by(Project.start_date.asc().nullslast()).all()

    # 3. 按年度分组构建路线图
    #   - 年度规划项目归入对应年度
    #   - 没有关联规划、但有时间线的项目按开始年份归入
    #   - 既无规划也无时间线的项目归入"其他"
    plan_map: dict[str, dict] = {}  # year → plan_group
    for plan in plans:
        year_str = str(plan.year)
        if year_str not in plan_map:
            plan_map[year_str] = {
                "year": plan.year,
                "plans": [],
                "projects": [],
            }
        plan_map[year_str]["plans"].append({
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
        })

    # 将项目关联到年度
    for p in projects:
        # 先尝试通过 annual_planning_ref 关联
        assigned = False
        if p.annual_planning_ref:
            for plan in plans:
                if p.annual_planning_ref == plan.name:
                    year_str = str(plan.year)
                    if year_str in plan_map:
                        plan_map[year_str]["projects"].append(_project_to_roadmap_item(p))
                        assigned = True
                    break

        if not assigned and p.start_date:
            # 按开始年份归入
            year_str = str(p.start_date.year)
            if year_str not in plan_map:
                plan_map[year_str] = {
                    "year": p.start_date.year,
                    "plans": [],
                    "projects": [],
                }
            plan_map[year_str]["projects"].append(_project_to_roadmap_item(p))
            assigned = True

        if not assigned:
            # 归入"其他"
            if "其他" not in plan_map:
                plan_map["其他"] = {
                    "year": 0,
                    "plans": [],
                    "projects": [],
                    "is_other": True,
                }
            plan_map["其他"]["projects"].append(_project_to_roadmap_item(p))

    # 4. 转为有序列表（按年份降序，"其他"在最后）
    roadmap_items = [v for k, v in sorted(plan_map.items(), key=lambda x: (
        0 if x[1].get("is_other") else 1,
        -x[1]["year"] if x[1]["year"] else 0,
    ))]

    return {
        "roadmap_items": roadmap_items,
        "total_plans": len(plans),
        "total_projects": len(projects),
    }
