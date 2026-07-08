"""驾驶舱仪表盘 — KPI卡片明细数据钻取"""
import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.approval import ApprovalRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱-KPI明细"])


def _get_kpi_in_progress(db: Session) -> list[dict[str, Any]]:
    """获取进行中策划明细"""
    in_progress_stages = [
        ProductPlanStage.DRAFT, ProductPlanStage.COMPETITOR,
        ProductPlanStage.DEFINITION, ProductPlanStage.COSTING,
        ProductPlanStage.TECH_INPUT, ProductPlanStage.PROJECT_INIT,
    ]
    plans = (
        db.query(ProductPlan)
        .filter(ProductPlan.status.in_(in_progress_stages))
        .order_by(ProductPlan.updated_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": p.id, "name": p.name, "market": p.market,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "series": p.series,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "type": "plan",
        }
        for p in plans
    ]


def _get_kpi_pending(db: Session) -> list[dict[str, Any]]:
    """获取待审批明细"""
    approvals = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.status == "pending", ApprovalRequest.request_type == "proposal")
        .order_by(ApprovalRequest.created_at.desc())
        .limit(200)
        .all()
    )
    result: list[dict[str, Any]] = []
    for a in approvals:
        name = f"审批#{a.id}"
        if a.request_data:
            try:
                data = json.loads(a.request_data) if isinstance(a.request_data, str) else a.request_data
                name = data.get("title") or data.get("name") or name
            except (json.JSONDecodeError, TypeError):
                pass
        result.append({
            "id": a.id, "name": name, "market": None,
            "status": a.status, "series": None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": None, "type": "approval",
        })
    return result


def _get_kpi_completed(db: Session) -> list[dict[str, Any]]:
    """获取本月已完成策划明细"""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    plans = (
        db.query(ProductPlan)
        .filter(ProductPlan.status == ProductPlanStage.RELEASED, ProductPlan.updated_at >= month_start)
        .order_by(ProductPlan.updated_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": p.id, "name": p.name, "market": p.market,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "series": p.series,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "type": "plan",
        }
        for p in plans
    ]


def _get_kpi_overdue(db: Session, today: date) -> list[dict[str, Any]]:
    """获取超期项目明细"""
    projects = (
        db.query(Project)
        .filter(
            Project.is_deleted == False, Project.target_end_date.isnot(None),
            Project.target_end_date < today, Project.status != "completed",
        )
        .order_by(Project.target_end_date)
        .limit(200)
        .all()
    )
    return [
        {
            "id": p.id, "name": p.name, "market": None,
            "status": p.status, "series": None, "code": p.code,
            "target_end_date": p.target_end_date.isoformat() if p.target_end_date else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "type": "project",
        }
        for p in projects
    ]


@router.get("/kpi-detail")
def get_kpi_detail(
    type: str = Query(..., description="KPI类型: in_progress / pending / completed / overdue"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """返回KPI卡片对应的明细数据，用于右侧抽屉表格展示"""
    today = date.today()
    if type == "in_progress":
        return _get_kpi_in_progress(db)
    if type == "pending":
        return _get_kpi_pending(db)
    if type == "completed":
        return _get_kpi_completed(db)
    if type == "overdue":
        return _get_kpi_overdue(db, today)
    raise HTTPException(status_code=400, detail=f"未知的KPI类型: {type}")
