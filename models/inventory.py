"""库存管理模型: 仓库 + 库存台账 + 库存流水"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Warehouse(Base):
    """仓库主数据"""
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="仓库编码")
    name = Column(String(200), nullable=False, comment="仓库名称")
    location = Column(String(500), nullable=True, comment="仓库位置")
    manager = Column(String(100), nullable=True, comment="仓库管理员")
    phone = Column(String(50), nullable=True, comment="联系电话")
    status = Column(String(20), default="active", comment="active/inactive")
    remark = Column(Text, nullable=True, comment="备注")
    is_deleted = Column(Integer, default=0, comment="软删除标记")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True,  # org_id)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)


class Inventory(Base):
    """库存台账 — 按物料+仓库维度的实时库存"""
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, comment="仓库ID")
    part_no = Column(String(50), nullable=False, index=True, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个",  # unit)
    # 库存数量
    qty = Column(Float, default=0.0, comment="当前库存量")
    available_qty = Column(Float, default=0.0, comment="可用库存量(qty - locked_qty)")
    locked_qty = Column(Float, default=0.0, comment="锁定/预留数量")
    # 库存参数
    min_stock = Column(Float, default=0.0, comment="最低库存警戒线")
    max_stock = Column(Float, default=0.0, comment="最高库存警戒线")
    reorder_point = Column(Float, default=0.0, comment="再订货点")
    # 库存价值
    unit_cost = Column(Float, default=0.0, comment="单价/成本价")
    total_value = Column(Float, default=0.0, comment="库存金额(qty × unit_cost)")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True,  # org_id)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    warehouse = relationship("Warehouse", lazy="joined")


class StorageLocation(Base):
    """库位管理 — 仓库内的具体存储位置"""
    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, comment="所属仓库ID")
    code = Column(String(50), nullable=False, comment="库位编码(如 A-01-01)")
    name = Column(String(200), nullable=True, comment="库位名称/描述")
    # 库位层级
    zone = Column(String(50), nullable=True, comment="区域(如 A/B/C/收货区/存储区)")
    row_label = Column(String(50), nullable=True, comment="排")
    shelf = Column(String(50), nullable=True, comment="层")
    bin = Column(String(50), nullable=True, comment="位")
    # 容量
    max_capacity = Column(Float, default=0.0, comment="最大容量")
    current_occupied = Column(Float, default=0.0, comment="当前占用量")
    capacity_unit = Column(String(20), default="个", comment="容量单位")
    # 库位类型
    location_type = Column(String(20), default="storage", comment="storage(存储)/receiving(收货)/picking(拣货)/return(退货)/quarantine(待检)")
    is_lockable = Column(Integer, default=0, comment="是否需要锁定管理(如贵重物料)")
    status = Column(String(20), default="active", comment="active/full/blocked/maintenance/inactive")
    # 排序
    sort_order = Column(Integer, default=0, comment="排序号(用于拣货路径优化)")
    remark = Column(Text, nullable=True, comment="备注")
    is_deleted = Column(Integer, default=0, comment="软删除标记")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True,  # org_id)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    warehouse = relationship("Warehouse", lazy="joined")


class ReplenishmentSuggestion(Base):
    """补货建议"""
    __tablename__ = "replenishment_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, comment="仓库ID")
    part_no = Column(String(50), nullable=False, index=True, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个",  # unit)
    # 库存状态
    current_qty = Column(Float, default=0.0, comment="当前库存量")
    reorder_point = Column(Float, default=0.0, comment="再订货点")
    min_stock = Column(Float, default=0.0, comment="最低库存线")
    avg_daily_usage = Column(Float, default=0.0, comment="日均消耗量")
    # 补货建议
    suggested_qty = Column(Float, default=0.0, comment="建议补货数量")
    lead_time_days = Column(Integer, default=7, comment="采购提前期(天)")
    expected_arrival = Column(DateTime, nullable=True, comment="预计到货日期")
    unit_cost = Column(Float, default=0.0, comment="单价")
    total_cost = Column(Float, default=0.0, comment="预计总金额")
    # 状态
    status = Column(String(20), default="pending", comment="pending/approved/purchased/cancelled")
    source = Column(String(20), default="auto", comment="auto(自动生成)/manual(手动创建)")
    remark = Column(Text, nullable=True, comment="备注")
    # 操作信息
    operator = Column(String(100), nullable=True, comment="操作人")
    approved_by = Column(String(100), nullable=True, comment="审批人")
    approved_at = Column(DateTime, nullable=True, comment="审批时间")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True,  # org_id)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    warehouse = relationship("Warehouse", lazy="joined")


class InventoryTransaction(Base):
    """库存流水 — 每笔出入库/调整都有记录"""
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, comment="仓库ID")
    part_no = Column(String(50), nullable=False, index=True, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个",  # unit)
    # 交易信息
    trans_type = Column(String(20), nullable=False, comment="in/out/adjust(入库/出库/调整)")
    qty = Column(Float, nullable=False, comment="变动数量(入库为正/出库为负)")
    balance_before = Column(Float, default=0.0, comment="变动前库存量")
    balance_after = Column(Float, default=0.0, comment="变动后库存量")
    # 来源单据
    ref_doc_type = Column(String(50), nullable=True, comment="来源单据类型(如: goods_receipt/inspection/adjustment)")
    ref_doc_id = Column(Integer, nullable=True, comment="来源单据ID")
    ref_doc_no = Column(String(50), nullable=True, comment="来源单据编号")
    # 经办信息
    operator = Column(String(100), nullable=True, comment="经办人")
    remark = Column(Text, nullable=True, comment="备注")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True,  # org_id)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
