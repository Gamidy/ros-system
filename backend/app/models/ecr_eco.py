"""Phase 2 — ECR/ECO 工程变更模型

ECR = Engineering Change Request（工程变更申请）
ECO = Engineering Change Order（工程变更指令）

状态机:
  ECR: DRAFT → SUBMITTED → REVIEWING → APPROVED/REJECTED → CONVERTED
  ECO: DRAFT → IMPLEMENTING → VERIFIED → EFFECTIVE → CLOSED/CANCELLED

关联:
  ECR 1:1 ECO（CONVERTED 时生成）
  ECO 1:N ECOItem（变更明细项）
  ECR 1:N ECRAttachment（附件）
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Date, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401


class ECRAttachment(Base):
    """ECR 附件"""
    __tablename__ = "ecr_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    ecr_id: Mapped[int] = mapped_column(ForeignKey("ecr_requests.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_size: Mapped[int] = mapped_column(default=0)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ecr: Mapped["ECRRequest"] = relationship(back_populates="attachments", lazy="selectin")


class ECRRequest(Base):
    """工程变更申请"""
    __tablename__ = "ecr_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    ecr_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    affected_products: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    affected_documents: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitter_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 关系
    submitter: Mapped["User"] = relationship(foreign_keys=[submitter_id], lazy="selectin")
    reviewer: Mapped[Optional["User"]] = relationship(foreign_keys=[reviewer_id], lazy="selectin")
    attachments: Mapped[List["ECRAttachment"]] = relationship(
        back_populates="ecr", cascade="all, delete-orphan", lazy="selectin"
    )
    eco: Mapped[Optional["ECO"]] = relationship(back_populates="ecr", uselist=False, lazy="selectin")


class ECO(Base):
    """工程变更指令"""
    __tablename__ = "ecos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ecr_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ecr_requests.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    implementation_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 关系
    ecr: Mapped[Optional["ECRRequest"]] = relationship(back_populates="eco", lazy="selectin")
    items: Mapped[List["ECOItem"]] = relationship(
        back_populates="eco", cascade="all, delete-orphan", lazy="selectin"
    )
    creator: Mapped["User"] = relationship(foreign_keys=[created_by], lazy="selectin")
    verifier: Mapped[Optional["User"]] = relationship(foreign_keys=[verified_by], lazy="selectin")


class ECOItem(Base):
    """ECO 明细项"""
    __tablename__ = "eco_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    eco_id: Mapped[int] = mapped_column(ForeignKey("ecos.id"), nullable=False)
    seq: Mapped[int] = mapped_column(nullable=False, default=0)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    object_type: Mapped[str] = mapped_column(String(20), nullable=False)
    object_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    object_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    object_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    eco: Mapped["ECO"] = relationship(back_populates="items", lazy="selectin")
