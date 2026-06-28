"""项目复盘API"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.project_review import ProjectReview
from app.schemas.project import ProjectReviewCreate, ProjectReviewOut, ProjectReviewUpdate

router = APIRouter(prefix="/projects/{pid}/reviews", tags=["项目复盘"])


def _review_to_out(r: ProjectReview) -> ProjectReviewOut:
    return ProjectReviewOut(
        id=r.id, project_id=r.project_id,
        review_type=r.review_type, phase_name=r.phase_name,
        what_went_well=r.what_went_well, what_could_improve=r.what_could_improve,
        key_lessons=r.key_lessons, action_items=r.action_items,
        overall_rating=r.overall_rating, reviewer=r.reviewer,
        review_date=r.review_date, is_shared=r.is_shared,
        created_at=r.created_at, updated_at=r.updated_at,
    )


@router.get("", response_model=list[ProjectReviewOut])
def list_reviews(pid: int, db: Session = Depends(get_db)):
    """获取项目复盘列表"""
    return [_review_to_out(r) for r in db.query(ProjectReview).filter(ProjectReview.project_id == pid).all()]


@router.post("", response_model=ProjectReviewOut)
def create_review(pid: int, data: ProjectReviewCreate, db: Session = Depends(get_db),
                  current_user: User = Depends(require_role("project_manager"))):
    """创建复盘记录"""
    r = ProjectReview(project_id=pid, **data.model_dump())
    db.add(r)
    db.flush()
    db.commit()
    db.refresh(r)
    return _review_to_out(r)


@router.get("/{review_id}", response_model=ProjectReviewOut)
def get_review(pid: int, review_id: int, db: Session = Depends(get_db)):
    r = db.query(ProjectReview).filter(
        ProjectReview.id == review_id, ProjectReview.project_id == pid
    ).first()
    if not r:
        raise HTTPException(404, "复盘记录不存在")
    return _review_to_out(r)


@router.put("/{review_id}", response_model=ProjectReviewOut)
def update_review(pid: int, review_id: int, data: ProjectReviewUpdate,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(require_role("project_manager"))):
    r = db.query(ProjectReview).filter(
        ProjectReview.id == review_id, ProjectReview.project_id == pid
    ).first()
    if not r:
        raise HTTPException(404, "复盘记录不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.flush()
    db.commit()
    db.refresh(r)
    return _review_to_out(r)


@router.delete("/{review_id}")
def delete_review(pid: int, review_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(require_role("project_manager"))):
    r = db.query(ProjectReview).filter(
        ProjectReview.id == review_id, ProjectReview.project_id == pid
    ).first()
    if not r:
        raise HTTPException(404, "复盘记录不存在")
    db.delete(r)
    db.commit()
    return {"message": "已删除"}
