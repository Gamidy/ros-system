"""P0 — 产品配置模型: 配置规则 + 配置组（关联表升级）"""

from sqlalchemy import String, Integer, ForeignKey, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.feature import FeatureOption, FeatureFamily
    from app.models.product import Series


# ── ConfigGroup ↔ FeatureFamily 多对多关联表 ──
config_group_families = Table(
    "config_group_families",
    Base.metadata,
    Column("config_group_id", Integer, ForeignKey("config_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("family_id", Integer, ForeignKey("feature_families.id", ondelete="CASCADE"), primary_key=True),
)


class ConfigGroup(Base, TimestampMixin):
    """配置组 — 将特征族绑定到产品系列，限定参与配置的特征范围"""

    __tablename__ = "config_groups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("series.id"), nullable=False, comment="所属产品系列"
    )

    # 关联表替代逗号分隔字符串
    families: Mapped[List["FeatureFamily"]] = relationship(
        "FeatureFamily", secondary=config_group_families, lazy="selectin"
    )

    @property
    def family_ids(self) -> List[int]:
        """计算属性：返回关联的特征族 ID 列表"""
        return [f.id for f in self.families] if self.families else []

    rules: Mapped[List["ConfigRule"]] = relationship(
        "ConfigRule", back_populates="group", cascade="all, delete-orphan", lazy="selectin"
    )


class ConfigRule(Base, TimestampMixin):
    """配置规则 — 特征选项之间的约束关系"""

    __tablename__ = "config_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("config_groups.id"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="requires | excludes"
    )
    source_option_id: Mapped[int] = mapped_column(
        ForeignKey("feature_options.id"), nullable=False, comment="源特征选项"
    )
    target_option_id: Mapped[int] = mapped_column(
        ForeignKey("feature_options.id"), nullable=False, comment="目标特征选项"
    )
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    group: Mapped["ConfigGroup"] = relationship(back_populates="rules")
    source_option: Mapped["FeatureOption"] = relationship(foreign_keys=[source_option_id], lazy="selectin")
    target_option: Mapped["FeatureOption"] = relationship(foreign_keys=[target_option_id], lazy="selectin")
