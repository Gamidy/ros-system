"""产品层级: Platform → Series → Model + BOM 物料"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import enum

from app.database import Base
from app.models.base import TimestampMixin


class ModelStatus(str, enum.Enum):
    DRAFT = "draft"
    RELEASED = "released"
    OBSOLETE = "obsolete"


class Platform(Base, TimestampMixin):
    """产品平台 (如: ODU-1HP 室外机平台)"""

    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="平台名称")
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, comment="平台编码")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    series_list: Mapped[List["Series"]] = relationship(
        "Series", back_populates="platform", cascade="all, delete-orphan"
    )


class Series(Base, TimestampMixin):
    """产品系列 (如: WALL-1HP 壁挂式系列)"""

    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)

    platform: Mapped["Platform"] = relationship(back_populates="series_list", lazy="selectin")
    models: Mapped[List["Model"]] = relationship(
        "Model", back_populates="series", cascade="all, delete-orphan"
    )


class Model(Base, TimestampMixin):
    """产品型号 (如: W09K-1 9K BTU 壁挂机)"""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), nullable=False)
    rated_capacity: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="额定制冷量 (BTU)")
    refrigerant: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="冷媒类型(R32/R410A)")
    status: Mapped[str] = mapped_column(String(20), default="draft", comment="draft/released/obsolete")

    series: Mapped["Series"] = relationship(back_populates="models", lazy="selectin")
