"""用户通知偏好配置 API

提供当前用户的通知偏好设置查询与更新。
- GET    /api/user/notification-prefs  返回当前用户所有偏好
- PUT    /api/user/notification-prefs  更新当前用户偏好（全量替换）
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_notification_pref import UserNotificationPref

router = APIRouter(prefix="/api/user", tags=["用户通知偏好"])


# ════════════════════════════════════════════════════════════
# Pydantic Schema
# ════════════════════════════════════════════════════════════


class NotificationPrefIn(BaseModel):
    """更新用户通知偏好的请求体"""
    channel: str = Field(..., min_length=1, max_length=32, description="通知通道: wecom / dingtalk / all")
    event_types: list[str] = Field(..., min_length=0, description="感兴趣的事件类型列表")
    enabled: bool = Field(True, description="是否启用该通道的推送")


class NotificationPrefOut(BaseModel):
    """用户通知偏好响应模型"""
    id: int
    user_id: int
    channel: str
    event_types: list
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
# API 端点
# ════════════════════════════════════════════════════════════


@router.get("/notification-prefs", response_model=list[NotificationPrefOut])
def get_notification_prefs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """获取当前用户的全部通知偏好配置"""
    prefs = (
        db.query(UserNotificationPref)
        .filter(UserNotificationPref.user_id == current_user.id)
        .all()
    )
    return prefs


@router.put("/notification-prefs", response_model=NotificationPrefOut)
def upsert_notification_pref(
    pref_in: NotificationPrefIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """创建或更新当前用户在指定通道的通知偏好（单通道全量替换）"""
    existing = (
        db.query(UserNotificationPref)
        .filter(
            UserNotificationPref.user_id == current_user.id,
            UserNotificationPref.channel == pref_in.channel,
        )
        .first()
    )

    if existing:
        existing.event_types = pref_in.event_types
        existing.enabled = pref_in.enabled
        pref = existing
    else:
        pref = UserNotificationPref(
            user_id=current_user.id,
            channel=pref_in.channel,
            event_types=pref_in.event_types,
            enabled=pref_in.enabled,
        )
        db.add(pref)

    db.commit()
    db.refresh(pref)
    return pref
