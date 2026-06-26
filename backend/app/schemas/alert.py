"""预警与通知管理 — Pydantic Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ═══════════════ 告警规则 ═══════════════

class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_type: str = Field(min_length=1, max_length=50)
    rule_type: str = Field(min_length=1, max_length=50)
    condition: str
    level: int = 2
    is_enabled: bool = True
    notify_channels: Optional[str] = None
    notify_users: Optional[str] = None


class AlertRuleOut(BaseModel):
    id: int
    name: str
    target_type: str
    rule_type: str
    condition: str
    level: int
    is_enabled: bool = True
    notify_channels: Optional[str] = None
    notify_users: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 告警记录 ═══════════════

class AlertOut(BaseModel):
    id: int
    rule_id: Optional[int] = None
    target_type: str
    target_id: int
    title: str
    level: int
    alert_type: str
    message: str
    is_read: bool = False
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════ 通知 ═══════════════

class NotificationOut(BaseModel):
    id: int
    alert_id: Optional[int] = None
    target_user: str
    channel: str
    title: str
    content: str
    is_sent: bool = False
    is_read: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
