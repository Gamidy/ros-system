"""特征族/特征选项模型 — 产品配置化基础"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

from app.database import Base
from app.models.base import TimestampMixin


class FeatureFamily(Base, TimestampMixin):
    """特征族 (如: 颜色、能效等级、电压)"""

    __tablename__ = "feature_families"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="特征族名称")
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, comment="编码")
    data_type: Mapped[str] = mapped_column(String(20), default="enum", comment="enum/int/float/string")
    is_required: Mapped[bool] = mapped_column(default=True, comment="是否必选")

    options: Mapped[List["FeatureOption"]] = relationship(
        "FeatureOption", back_populates="family", cascade="all, delete-orphan", lazy="selectin"
    )


class FeatureOption(Base, TimestampMixin):
    """特征选项 (如: R32、R410A、220V)"""

    __tablename__ = "feature_options"
    __table_args__ = (
        UniqueConstraint("family_id", "value", name="uq_family_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("feature_families.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    family: Mapped["FeatureFamily"] = relationship(back_populates="options")
