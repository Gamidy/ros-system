"""盘点管理模型: 盘点计划 + 盘点明细"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class InventoryCount(Base):
    """盘点计划单"""
    __tablename__ = "inventory_counts"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    count_no = Column(String(30), unique=True, index=True, nullable=False, comment="盘点单号 PD-YYYYMMDD-XXXX")
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, comment="盘点仓库ID")
    warehouse_name = Column(String(200), nullable=True, comment="仓库名称(快照)")

    count_type = Column(String(20), default="partial", comment="full=全盘/partial=抽盘")
    status = Column(String(20), default="draft", comment="draft/pending/in_progress/completed/cancelled")

    total_items = Column(Integer, default=0, comment="盘点项数")
    matched_count = Column(Integer, default=0, comment="一致项数")
    discrepancy_count = Column(Integer, default=0, comment="差异项数")
    total_discrepancy_value = Column(Float, default=0.0, comment="差异总金额")

    count_date = Column(DateTime, server_default=func.now(), comment="盘点日期")
    counted_by = Column(String(100), nullable=True, comment="盘点人")
    remark = Column(Text, nullable=True, comment="备注")

    created_by = Column(String(50), nullable=True,  # created_by)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    items = relationship("InventoryCountItem", back_populates="count", cascade="all, delete-orphan")


class InventoryCountItem(Base):
    """盘点明细 — 每行物料的实际盘点记录"""
    __tablename__ = "inventory_count_items"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    count_id = Column(Integer, ForeignKey("inventory_counts.id"), nullable=False,  # count_id)

    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True, comment="库存台账ID")
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个",  # unit)

    system_qty = Column(Float, default=0.0, comment="系统数量")
    actual_qty = Column(Float, default=0.0, comment="实盘数量")
    diff_qty = Column(Float, default=0.0, comment="差异数量(actual-system)")
    unit_cost = Column(Float, default=0.0, comment="单价")
    diff_value = Column(Float, default=0.0, comment="差异金额")

    status = Column(String(20), default="pending", comment="pending=待盘/matched=一致/discrepancy=差异/adjusted=已调整")
    remark = Column(String(500), nullable=True, comment="备注")
    adjusted_at = Column(DateTime, nullable=True, comment="调整时间")

    count = relationship("InventoryCount", back_populates="items")
