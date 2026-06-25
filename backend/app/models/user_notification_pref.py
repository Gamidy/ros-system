"""用户通知偏好配置模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, func, ForeignKey, UniqueConstraint
from app.core.database import Base


class UserNotificationPref(Base):
    """用户通知偏好 — 每个用户可按通道配置感兴趣的事件类型"""
    __tablename__ = "user_notification_prefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    channel = Column(String(32), nullable=False, default="all", comment="通知通道: wecom / dingtalk / all")
    event_types = Column(JSON, nullable=False, default=list, comment="感兴趣的事件类型列表，如 [\"plan.approved\", \"test.done_with_ng\"]")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用该通道的推送")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_user_channel"),
    )

    def __repr__(self):
        return (
            f"<UserNotificationPref(id={self.id}, user_id={self.user_id}, "
            f"channel={self.channel}, enabled={self.enabled})>"
        )
