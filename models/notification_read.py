"""已读/未读跨渠道同步模型

每个用户在每个渠道上的通知已读状态独立记录。
标记一个渠道已读时，自动同步标记其他所有渠道。
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, UniqueConstraint, func,
)
from app.core.database import Base


# ── 渠道类型常量 ──────────────────────────────────────────────────────────

# 复用 user_notification_pref 中的常量以避免重复定义
from app.models.user_notification_pref import CHANNEL_TYPES as _CHANNEL_TYPES

CHANNEL_TYPES: list[str] = _CHANNEL_TYPES


class NotificationReadStatus(Base):
    """通知已读状态 — 每个用户在每个渠道上的通知已读标记

    联合唯一索引 (notification_id, user_id, channel_type) 确保不会重复标记。
    跨渠道同步策略：标记一个渠道已读时，为该用户在所有渠道上都创建已读记录。
    """
    __tablename__ = "notification_read_status"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    notification_id = Column(
        String(64), nullable=False, index=True,
        comment="通知 ID（来自 notifications 表的主键，字符串化）",
    )
    user_id = Column(
        String(100), nullable=False, index=True,
        comment="用户标识（username）",
    )
    channel_type = Column(
        String(32), nullable=False,
        comment="推送渠道: wecom / dingtalk / email / websocket",
    )
    read_at = Column(
        DateTime, nullable=False, server_default=func.now(),
        comment="标记已读的时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "notification_id", "user_id", "channel_type",
            name="uq_notif_read_user_channel",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationReadStatus(id={self.id}, "
            f"notification_id={self.notification_id}, "
            f"user_id={self.user_id}, "
            f"channel_type={self.channel_type}, "
            f"read_at={self.read_at})>"
        )
