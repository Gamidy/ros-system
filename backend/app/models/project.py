"""项目/WBS/任务/阶段门模型"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime, timezone
import enum

from app.database import Base
from app.models.base import TimestampMixin


class PhaseEnum(str, enum.Enum):
    NPR = "npr"
    CONCEPT = "concept"
    PLAN = "plan"
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    RELEASE = "release"
    LIFECYCLE = "lifecycle"


class GateDecision(str, enum.Enum):
    GO = "go"
    KILL = "kill"
    REDIRECT = "redirect"
    HOLD = "hold"
    PENDING = "pending"


class Project(Base, TimestampMixin):
    """策划项目"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("models.id"), nullable=True)
    current_phase: Mapped[str] = mapped_column(SAEnum(PhaseEnum), default=PhaseEnum.NPR)
    project_class: Mapped[str] = mapped_column(String(5), default="T", comment="T/A/B/C")
    status: Mapped[str] = mapped_column(String(20), default="active")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    wbs_nodes: Mapped[List["WBSNode"]] = relationship("WBSNode", back_populates="project", cascade="all, delete-orphan")
    gates: Mapped[List["Gate"]] = relationship("Gate", back_populates="project", cascade="all, delete-orphan")


class WBSNode(Base, TimestampMixin):
    """WBS工作包 (树形结构)"""

    __tablename__ = "wbs_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("wbs_nodes.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), default="work_package", comment="phase/deliverable/work_package/task")
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    project: Mapped["Project"] = relationship(back_populates="wbs_nodes")
    parent: Mapped[Optional["WBSNode"]] = relationship("WBSNode", back_populates="children", remote_side=[id])
    children: Mapped[List["WBSNode"]] = relationship("WBSNode", back_populates="parent", lazy="selectin")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="wbs_node", cascade="all, delete-orphan")


class Task(Base, TimestampMixin):
    """任务卡"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wbs_id: Mapped[int] = mapped_column(ForeignKey("wbs_nodes.id"), nullable=False)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo", comment="todo/in_progress/done/blocked")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    wbs_node: Mapped["WBSNode"] = relationship(back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship("User")


class Gate(Base, TimestampMixin):
    """阶段门评审记录"""

    __tablename__ = "gates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(SAEnum(PhaseEnum), nullable=True)
    gate_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="M1~M9")
    gate_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/passed/failed")
    decision: Mapped[str] = mapped_column(SAEnum(GateDecision), default=GateDecision.PENDING)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="gates")
