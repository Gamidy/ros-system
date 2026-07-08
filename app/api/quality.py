"""质量管理 API — 仪表盘"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/quality", tags=["质量管理"])

@router.get("/dashboard", response_model=dict)
def quality_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """质量仪表盘"""
    return {
        "total_8d_reports": 0,
        "open_8d_reports": 0,
        "total_iqc": 0,
        "open_complaints": 0,
        "open_tasks": 0,
    }
