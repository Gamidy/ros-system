"""用户通知偏好配置 API

提供当前用户的通知偏好设置查询与批量更新。
- GET /api/user/notification-prefs   获取当前用户所有偏好
- PUT /api/user/notification-prefs   批量更新偏好（接收数组）

默认偏好逻辑：未显式设置的行视为 enabled=true。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_notification_pref import (
    UserNotificationPref,
    EVENT_TYPES,
    CHANNEL_TYPES,
)

router = APIRouter(prefix="/api/user", tags=["用户通知偏好"])


# ════════════════════════════════════════════════════════════
# Pydantic Schema
# ════════════════════════════════════════════════════════════


class NotificationPrefItem(BaseModel):
    """单条通知偏好"""
    event_type: str = Field(..., description="事件类型")
    channel_type: str = Field(..., description="推送渠道")
    enabled: bool = Field(True, description="是否启用")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError(f"无效的事件类型: {v}，可选: {EVENT_TYPES}")
        return v

    @field_validator("channel_type")
    @classmethod
    def validate_channel_type(cls, v: str) -> str:
        if v not in CHANNEL_TYPES:
            raise ValueError(f"无效的渠道类型: {v}，可选: {CHANNEL_TYPES}")
        return v


class NotificationPrefOut(BaseModel):
    """通知偏好响应模型"""
    id: int
    user_id: int
    event_type: str
    channel_type: str
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationPrefBatchIn(BaseModel):
    """批量更新请求体"""
    prefs: list[NotificationPrefItem] = Field(
        ...,
        min_length=0,
        max_length=100,
        description="偏好列表（全量替换）",
    )


# ════════════════════════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════════════════════════


def _ensure_default_prefs(db: Session, user_id: int) -> None:
    """确保用户对所有事件-渠道组合有默认记录（未创建过的才插入）"""
    existing = (
        db.query(UserNotificationPref)
        .filter(UserNotificationPref.user_id == user_id)
        .all()
    )
    existing_set: set[tuple[str, str]] = {
        (p.event_type, p.channel_type) for p in existing
    }

    new_rows: list[UserNotificationPref] = []
    for et in EVENT_TYPES:
        for ct in CHANNEL_TYPES:
            if (et, ct) not in existing_set:
                new_rows.append(
                    UserNotificationPref(
                        user_id=user_id,
                        event_type=et,
                        channel_type=ct,
                        enabled=True,
                    )
                )

    if new_rows:
        db.add_all(new_rows)
        db.commit()


# ════════════════════════════════════════════════════════════
# API 端点
# ════════════════════════════════════════════════════════════


@router.get(
    "/notification-prefs",
    response_model=list[NotificationPrefOut],
)
def get_notification_prefs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserNotificationPref]:
    """获取当前用户的全部通知偏好配置（自动补齐默认记录）"""
    _ensure_default_prefs(db, current_user.id)
    prefs = (
        db.query(UserNotificationPref)
        .filter(UserNotificationPref.user_id == current_user.id)
        .order_by(UserNotificationPref.event_type, UserNotificationPref.channel_type)
        .all()
    )
    return prefs


@router.put(
    "/notification-prefs",
    response_model=list[NotificationPrefOut],
)
def update_notification_prefs(
    body: NotificationPrefBatchIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserNotificationPref]:
    """批量更新当前用户的通知偏好（全量替换匹配的记录）"""
    user_id = current_user.id

    for item in body.prefs:
        existing = (
            db.query(UserNotificationPref)
            .filter(
                UserNotificationPref.user_id == user_id,
                UserNotificationPref.event_type == item.event_type,
                UserNotificationPref.channel_type == item.channel_type,
            )
            .first()
        )

        if existing:
            existing.enabled = item.enabled
        else:
            db.add(
                UserNotificationPref(
                    user_id=user_id,
                    event_type=item.event_type,
                    channel_type=item.channel_type,
                    enabled=item.enabled,
                )
            )

    db.commit()

    # 返回全量
    all_prefs = (
        db.query(UserNotificationPref)
        .filter(UserNotificationPref.user_id == user_id)
        .order_by(UserNotificationPref.event_type, UserNotificationPref.channel_type)
        .all()
    )
    return all_prefs
