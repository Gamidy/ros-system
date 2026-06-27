"""通知分组 & 免打扰时段 API

Endpoints:
- GET    /api/user/notification-categories   获取通知分类列表
- GET    /api/user/notification-dnd          获取当前用户免打扰配置
- PUT    /api/user/notification-dnd          更新免打扰配置
"""
from datetime import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification_grouping import (
    NotificationCategory,
    NotificationDoNotDisturb,
    DEFAULT_CATEGORIES,
)

router = APIRouter(prefix="/api/user", tags=["通知分组与免打扰"])


# ════════════════════════════════════════════════════════════
# Pydantic Schema
# ════════════════════════════════════════════════════════════


class NotificationCategoryOut(BaseModel):
    id: int
    event_type: str
    category: str
    category_label: str
    priority: int
    is_system: bool

    class Config:
        from_attributes = True


class DoNotDisturbOut(BaseModel):
    id: int
    enabled: bool
    start_time: str
    end_time: str
    timezone: str
    min_priority: int

    class Config:
        from_attributes = True


class DoNotDisturbUpdate(BaseModel):
    enabled: Optional[bool] = Field(None, description="是否启用免打扰")
    start_time: Optional[str] = Field(None, description="开始时间 HH:MM")
    end_time: Optional[str] = Field(None, description="结束时间 HH:MM")
    timezone: Optional[str] = Field(None, description="时区")
    min_priority: Optional[int] = Field(None, ge=0, le=2, description="最低推送优先级")

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("时间格式应为 HH:MM")
        try:
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except ValueError:
            raise ValueError("时间格式无效，应为 HH:MM (0-23:0-59)")
        return v


# ════════════════════════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════════════════════════


def _seed_default_categories(db: Session) -> None:
    """确保默认分类存在（幂等）"""
    for cat_data in DEFAULT_CATEGORIES:
        existing = db.query(NotificationCategory).filter(
            NotificationCategory.event_type == cat_data["event_type"],
        ).first()
        if not existing:
            db.add(NotificationCategory(**cat_data))
    db.commit()


# ════════════════════════════════════════════════════════════
# API 端点
# ════════════════════════════════════════════════════════════


@router.get(
    "/notification-categories",
    response_model=list[NotificationCategoryOut],
)
def get_notification_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationCategory]:
    """获取所有通知类型→分类映射"""
    _seed_default_categories(db)
    return db.query(NotificationCategory).order_by(NotificationCategory.id).all()


@router.get(
    "/notification-dnd",
    response_model=DoNotDisturbOut,
)
def get_dnd_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDoNotDisturb:
    """获取当前用户免打扰配置（自动创建默认）"""
    config = db.query(NotificationDoNotDisturb).filter(
        NotificationDoNotDisturb.user_id == current_user.id,
    ).first()
    if not config:
        config = NotificationDoNotDisturb(
            user_id=current_user.id,
            enabled=False,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="Asia/Shanghai",
            min_priority=1,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put(
    "/notification-dnd",
    response_model=DoNotDisturbOut,
)
def update_dnd_config(
    body: DoNotDisturbUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationDoNotDisturb:
    """更新当前用户免打扰配置"""
    config = db.query(NotificationDoNotDisturb).filter(
        NotificationDoNotDisturb.user_id == current_user.id,
    ).first()
    if not config:
        config = NotificationDoNotDisturb(user_id=current_user.id)
        db.add(config)
        db.flush()

    if body.enabled is not None:
        config.enabled = body.enabled
    if body.start_time is not None:
        parts = body.start_time.split(":")
        config.start_time = time(int(parts[0]), int(parts[1]))
    if body.end_time is not None:
        parts = body.end_time.split(":")
        config.end_time = time(int(parts[0]), int(parts[1]))
    if body.timezone is not None:
        config.timezone = body.timezone
    if body.min_priority is not None:
        config.min_priority = body.min_priority

    db.commit()
    db.refresh(config)
    return config
