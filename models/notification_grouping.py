"""通知分组与免打扰时段模型

通知分组（type→category）允许将事件类型归类到业务分类，
免打扰时段允许用户在指定时间段内暂停非紧急通知推送。
"""
from datetime import time
from sqlalchemy import (
    Column, Integer, String, Boolean, Time, DateTime, Text,
    ForeignKey, UniqueConstraint, func,
)
from app.core.database import Base


class NotificationCategory(Base):
    """通知分类 — 事件类型 → 业务分类映射"""
    __tablename__ = "notification_categories"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    event_type = Column(
        String(32), nullable=False, unique=True, index=True,
        comment="事件类型 (approval_request / plan_submitted / review_due / alert)",
    )
    category = Column(
        String(32), nullable=False, index=True,
        comment="业务分类 (approval / planning / review / system)",
    )
    category_label = Column(
        String(64), nullable=False, default="",
        comment="分类中文名",
    )
    priority = Column(
        Integer, nullable=False, default=0,
        comment="优先级 (0=normal, 1=important, 2=critical)",
    )
    is_system = Column(
        Boolean, nullable=False, default=False,
        comment="系统级通知（不可关闭/不可免打扰）",
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(,  # updated_at)

    def __repr__(self) -> str:
        return (
            f"<NotificationCategory(id={self.id}, event_type={self.event_type}, "
            f"category={self.category}, priority={self.priority})>"
        )


class NotificationDoNotDisturb(Base):
    """用户免打扰时段配置"""
    __tablename__ = "notification_dnd"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    enabled = Column(Boolean, nullable=False, default=False, comment="是否启用免打扰")
    start_time = Column(Time, nullable=False, default=time(22, 0), comment="免打扰开始时间")
    end_time = Column(Time, nullable=False, default=time(8, 0), comment="免打扰结束时间")
    timezone = Column(String(32), nullable=False, default="Asia/Shanghai", comment="时区")
    # 在免打扰期间，低于此优先级的通知不推送
    min_priority = Column(
        Integer, nullable=False, default=1,
        comment="免打扰期间最低推送优先级 (0=不屏蔽, 1=仅重要, 2=仅紧急)",
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(,  # updated_at)

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_dnd_user"),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationDoNotDisturb(id={self.id}, user_id={self.user_id}, "
            f"enabled={self.enabled}, {self.start_time}-{self.end_time})>"
        )


# ── 默认分类映射 ──────────────────────────────────────────────────

DEFAULT_CATEGORIES: list[dict] = [
    {"event_type": "approval_request", "category": "approval", "category_label": "审批", "priority": 2, "is_system": True},
    {"event_type": "plan_submitted",   "category": "planning",  "category_label": "策划",  "priority": 0, "is_system": False},
    {"event_type": "review_due",       "category": "review",    "category_label": "评审",   "priority": 1, "is_system": False},
    {"event_type": "alert",            "category": "system",    "category_label": "系统",   "priority": 2, "is_system": True},
]
