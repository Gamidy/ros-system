"""物料主数据 + 超级BOM节点"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

from app.database import Base
from app.models.base import TimestampMixin


class Material(Base, TimestampMixin):
    """物料主数据"""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    material_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, comment="结构/电控/电器/包材/辅料")
    specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(10), default="pcs")
    status: Mapped[str] = mapped_column(String(20), default="active")


class SuperBOMNode(Base, TimestampMixin):
    """超级BOM节点 (150% BOM — 树形结构)"""

    __tablename__ = "super_bom_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), nullable=False, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("super_bom_nodes.id"), nullable=True, comment="父节点(树结构)"
    )
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    node_type: Mapped[str] = mapped_column(String(20), default="assembly", comment="assembly/component/optional")
    sequence: Mapped[int] = mapped_column(Integer, default=0, comment="同层排序")
    expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="特征约束表达式(占位Phase 1)")

    # 关系
    children: Mapped[List["SuperBOMNode"]] = relationship(
        "SuperBOMNode", back_populates="parent", lazy="selectin"
    )
    parent: Mapped[Optional["SuperBOMNode"]] = relationship(
        "SuperBOMNode", back_populates="children", remote_side=[id]
    )
    material: Mapped["Material"] = relationship(lazy="selectin")
