"""用户通知偏好配置模型

每个用户可针对每种事件类型，分别设置各推送渠道的开关。
- event_type:  事件类型（approval_request / plan_submitted / review_due / alert）
- channel_type: 推送渠道（wecom / dingtalk / email / websocket）
- 联合唯一 (user_id, event_type, channel_type)
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, UniqueConstraint, func,
)
from app.core.database import Base


# ── 常量 ──────────────────────────────────────────────────────────────────

EVENT_TYPES: list[str] = [
    "approval_request",
    "plan_submitted",
    "review_due",
    "alert",
    "standard_update",
]

CHANNEL_TYPES: list[str] = [
    "wecom",
    "dingtalk",
    "email",
    "websocket",
]

EVENT_TYPE_LABELS: dict[str, str] = {
    "approval_request": "审批请求",
    "plan_submitted": "策划提交",
    "review_due": "评审到期",
    "alert": "系统预警",
}

CHANNEL_TYPE_LABELS: dict[str, str] = {
    "wecom": "企业微信",
    "dingtalk": "钉钉",
    "email": "邮件",
    "websocket": "站内通知",
}


# ── 模型 ──────────────────────────────────────────────────────────────────


class UserNotificationPref(Base):
    """用户通知偏好 — 每个事件-渠道组合一条记录"""
    __tablename__ = "user_notification_prefs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    event_type = Column(
        String(32),
        nullable=False,
        comment="事件类型: approval_request / plan_submitted / review_due / alert",
    )
    channel_type = Column(
        String(32),
        nullable=False,
        comment="推送渠道: wecom / dingtalk / email / websocket",
    )
    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用该事件-渠道推送",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "event_type", "channel_type",
            name="uq_user_event_channel",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserNotificationPref(id={self.id}, user_id={self.user_id}, "
            f"event_type={self.event_type}, channel_type={self.channel_type}, "
            f"enabled={self.enabled})>"
        )
