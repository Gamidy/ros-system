"""审计日志查询 API — 仅 admin 可访问"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.audit import AuditLog
from app.models.user import User
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/audit-logs", tags=["审计日志"])


class AuditLogOut(BaseModel):
    id: int
    username: str
    role: str
    method: str
    path: str
    status_code: int
    action_type: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=dict)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    action_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    username: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    days: Optional[int] = Query(None, ge=1, le=90),
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """查询审计日志（仅 admin 可访问）"""
    # 权限检查
    from app.core.permissions import is_super_role
    if not is_super_role(current_user.role):
        raise HTTPException(status_code=403, detail="仅管理员可查看审计日志")

    query = db.query(AuditLog)

    # 筛选
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
    if method:
        query = query.filter(AuditLog.method == method.upper())
    if status_code:
        query = query.filter(AuditLog.status_code == status_code)
    if days:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(AuditLog.created_at >= cutoff)
    if keyword:
        query = query.filter(
            AuditLog.path.ilike(f"%{keyword}%")
            | AuditLog.detail.ilike(f"%{keyword}%")
        )

    total = query.count()
    items = (
        query.order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [AuditLogOut.model_validate(a) for a in items],
    }


@router.get("/stats", response_model=dict)
def audit_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """审计日志统计（仅 admin）"""
    from app.core.permissions import is_super_role
    if not is_super_role(current_user.role):
        raise HTTPException(status_code=403, detail="仅管理员可查看审计日志")

    cutoff = datetime.now() - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.created_at >= cutoff)

    # 按操作类型统计
    from sqlalchemy import func
    by_action = (
        query.with_entities(AuditLog.action_type, func.count(AuditLog.id))
        .group_by(AuditLog.action_type)
        .all()
    )
    # 按资源类型统计
    by_resource = (
        query.with_entities(AuditLog.resource_type, func.count(AuditLog.id))
        .group_by(AuditLog.resource_type)
        .all()
    )
    # 按天统计
    from sqlalchemy import cast, Date
    by_day = (
        query.with_entities(cast(AuditLog.created_at, Date), func.count(AuditLog.id))
        .group_by(cast(AuditLog.created_at, Date))
        .order_by(cast(AuditLog.created_at, Date))
        .all()
    )

    return {
        "total": query.count(),
        "by_action": {k: v for k, v in by_action},
        "by_resource": {k: v for k, v in by_resource},
        "by_day": {str(k): v for k, v in by_day},
    }
