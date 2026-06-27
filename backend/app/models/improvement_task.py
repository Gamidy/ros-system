"""ImprovementTask — 复盘改进任务追踪模型

复盘问题点自动转为改进任务，跟踪是否闭环。
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, DateTime, Date,
    ForeignKey, Enum as SAEnum, func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TaskPriority(str, enum.Enum):
    """改进任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, enum.Enum):
    """改进任务状态"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ImprovementTask(Base):
    """改进任务 — 复盘发现的问题点转为可追踪的改进任务"""
    __tablename__ = "improvement_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(
        String(36),
        ForeignKey("product_plan_reviews.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联复盘ID",
    )
    description = Column(Text, nullable=False, comment="改进任务描述")
    assigned_to = Column(
        String(50),
        ForeignKey("users.username", ondelete="SET NULL"),
        nullable=True,
        comment="负责人用户名",
    )
    priority = Column(
        SAEnum(TaskPriority),
        default=TaskPriority.MEDIUM,
        nullable=False,
        comment="优先级: high/medium/low",
    )
    status = Column(
        SAEnum(TaskStatus),
        default=TaskStatus.OPEN,
        nullable=False,
        comment="状态: open/in_progress/resolved/closed",
    )
    due_date = Column(Date, nullable=True, comment="截止日期")
    resolved_at = Column(DateTime, nullable=True, comment="解决时间")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    review = relationship("ProductPlanReview", backref="improvement_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to])
