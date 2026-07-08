"""项目知识库 — 共享复盘/经验查询"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.project_review import ProjectReview
from app.models.project import Project, Task

router = APIRouter(prefix="/knowledge-base", tags=["知识库"])


@router.get("/lessons")
def list_lessons(
    review_type: str | None = None,
    keyword: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """查询共享的复盘经验库"""
    q = db.query(ProjectReview).filter(ProjectReview.is_shared == True)

    if review_type:
        q = q.filter(ProjectReview.review_type == review_type)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            ProjectReview.what_went_well.ilike(like)
            | ProjectReview.what_could_improve.ilike(like)
            | ProjectReview.key_lessons.ilike(like)
        )

    reviews = q.order_by(ProjectReview.created_at.desc()).limit(limit).all()

    result = []
    for r in reviews:
        p = db.query(Project).filter(Project.id == r.project_id).first()
        result.append({
            "id": r.id,
            "project_id": r.project_id,
            "project_code": p.code if p else None,
            "project_name": p.name if p else None,
            "review_type": r.review_type,
            "phase_name": r.phase_name,
            "what_went_well": r.what_went_well,
            "what_could_improve": r.what_could_improve,
            "key_lessons": r.key_lessons,
            "overall_rating": r.overall_rating,
            "reviewer": r.reviewer,
            "review_date": str(r.review_date) if r.review_date else None,
            "created_at": str(r.created_at.date()) if r.created_at else None,
        })

    return result


@router.get("/search")
def global_search(
    q: str = Query("", description="搜索关键词"),
    module: str | None = Query(None, description="模块: projects/tasks/milestones/reviews"),
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """全局搜索 — 跨模块搜索项目/任务/复盘"""
    results: dict = {}

    if not module or module == "projects":
        projects = db.query(Project).filter(
            Project.is_deleted == False,
            (Project.name.ilike(f"%{q}%")) | (Project.code.ilike(f"%{q}%"))
        ).limit(limit).all()
        results["projects"] = [{"id": p.id, "code": p.code, "name": p.name, "status": p.status, "_type": "project"} for p in projects]

    if not module or module == "tasks":
        tasks = db.query(Task).filter(Task.title.ilike(f"%{q}%")).limit(limit).all()
        results["tasks"] = [{"id": t.id, "project_id": t.project_id, "title": t.title, "status": t.status, "assignee": t.assignee, "_type": "task"} for t in tasks]

    if not module or module == "reviews":
        reviews = db.query(ProjectReview).filter(
            ProjectReview.is_shared == True,
            (ProjectReview.what_went_well.ilike(f"%{q}%"))
            | (ProjectReview.what_could_improve.ilike(f"%{q}%"))
            | (ProjectReview.key_lessons.ilike(f"%{q}%"))
        ).limit(limit).all()
        results["reviews"] = [{"id": r.id, "project_id": r.project_id, "review_type": r.review_type, "what_went_well": r.what_went_well[:200], "_type": "review"} for r in reviews]

    return results


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
):
    """获取项目团队角色列表"""
    roles = [
        {"label": "项目经理", "value": "项目经理", "sys_role": "project_manager"},
        {"label": "系统工程师", "value": "系统工程师", "sys_role": "systems_engineer"},
        {"label": "结构工程师", "value": "结构工程师", "sys_role": "structural_engineer"},
        {"label": "电控工程师", "value": "电控工程师", "sys_role": "electrical_control_engineer"},
        {"label": "电气工程师", "value": "电气工程师", "sys_role": "electrical_engineer"},
        {"label": "品质工程师", "value": "品质工程师", "sys_role": "quality_engineer"},
        {"label": "工艺工程师", "value": "工艺工程师", "sys_role": "process_engineer"},
        {"label": "采购", "value": "采购", "sys_role": "procurement"},
        {"label": "生产", "value": "生产", "sys_role": "production"},
    ]
    return roles
