"""已读/未读跨渠道同步 — Pydantic Schema

提供通知已读标记的请求与响应模型。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class NotificationReadRequest(BaseModel):
    """标记通知已读请求"""
    notification_id: str = Field(
        ..., min_length=1, max_length=64,
        description="通知 ID（notifications 表主键的字符串形式）",
    )
    channel_type: str = Field(
        ..., min_length=1, max_length=32,
        description="当前渠道类型: wecom / dingtalk / email / websocket",
    )


class NotificationReadOut(BaseModel):
    """标记已读响应"""
    ok: bool = True
    notification_id: str
    user_id: str
    synced_channels: list[str] = Field(
        default_factory=list,
        description="同步标记已读的渠道列表",
    )
    read_at: Optional[datetime] = None


class NotificationReadStatusOut(BaseModel):
    """单条已读状态（供列表查询使用）"""
    channel_type: str
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
