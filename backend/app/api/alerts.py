"""通知管理 API"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.alert import Notification
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["通知管理"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    target_user: str = Query("", description="目标用户"),
    is_read: bool = Query(None, description="是否已读"),
    channel: str = Query("", description="通知渠道"),
    db: Session = Depends(get_db),
):
    q = db.query(Notification)
    if target_user:
        q = q.filter(Notification.target_user == target_user)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    if channel:
        q = q.filter(Notification.channel == channel)
    return q.order_by(Notification.created_at.desc()).all()


@router.patch("/{nid}/read")
def mark_notification_read(
    nid: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    notif = db.query(Notification).filter(Notification.id == nid).first()
    if not notif:
        raise HTTPException(status_code=404, detail="通知记录不存在")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
