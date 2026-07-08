"""InventorySnapshot — 库存快照模型

定期保存物料库存快照，用于计算周转率等分析指标。
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, func
from app.core.database import Base


class InventorySnapshot(Base):
    """库存快照 — 按物料+日期存储的库存及出库数据"""
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True)
    material_code = Column(String(50), comment="物料编码")
    material_name = Column(String(200), nullable=True, comment="物料名称")
    snapshot_date = Column(Date, comment="快照日期")
    stock_qty = Column(Integer, default=0, comment="库存数量")
    monthly_out_qty = Column(Integer, default=0, comment="月出库数量")
    turnover_rate = Column(Float, nullable=True, comment="周转率")
    created_at = Column(DateTime, server_default=func.now())
