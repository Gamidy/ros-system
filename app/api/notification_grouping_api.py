"""通知分组与免打扰 API"""
from datetime import time, date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, field_serializer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification_grouping import (
    NotificationCategory,
    NotificationDoNotDisturb,
    DEFAULT_CATEGORIES,
)

router = APIRouter(prefix="/user", tags=["通知分组与免打扰"])


# ── Schemas ──

class NotificationCategoryOut(BaseModel):
    id: int
    event_type: str
    category: str
    description: Optional[str] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True


class DoNotDisturbOut(BaseModel):
    id: int
    enabled: bool
    start_time: Any  # datetime.time 输入 → str 输出
    end_time: Any    # datetime.time 输入 → str 输出
    timezone: str
    min_priority: int

    class Config:
        from_attributes = True

    @field_serializer("start_time", "end_time")
    def serialize_time(self, v: Any) -> str:
        return str(v) if v else "00:00"


class DoNotDisturbUpdate(BaseModel):
    enabled: Optional[bool] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    timezone: Optional[str] = None
    min_priority: Optional[int] = Field(None, ge=0, le=5)


# ── 种子数据（如果表为空则写入）─

def _seed_default_categories(db: Session) -> None:
    existing = db.query(NotificationCategory).count()
    if existing > 0:
        return
    for item in DEFAULT_CATEGORIES:
        db.add(NotificationCategory(
            event_type=item["event_type"], category=item["category"],
        ))
    db.commit()


# ── API 端点 ──

@router.get("/notification-categories", response_model=list[NotificationCategoryOut])
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
