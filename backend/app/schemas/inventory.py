"""库存管理 — Pydantic Schema"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════ 仓库管理 ═══════════════

class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    location: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class WarehouseOut(BaseModel):
    id: int
    code: str
    name: str
    location: Optional[str] = None
    manager: Optional[str] = None
    phone: Optional[str] = None
    status: str
    remark: Optional[str] = None
    is_deleted: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


# ═══════════════ 库存台账 ═══════════════

class InventoryOut(BaseModel):
    id: int
    warehouse_id: int
    warehouse_name: Optional[str] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str
    qty: float
    available_qty: float
    locked_qty: float
    min_stock: float
    max_stock: float
    reorder_point: float
    unit_cost: float
    total_value: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


class InventoryFilterParams(BaseModel):
    warehouse_id: Optional[int] = None
    part_no: Optional[str] = None
    part_name: Optional[str] = None
    low_stock: Optional[bool] = None  # True = qty <= min_stock
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class InventoryAdjust(BaseModel):
    """库存调整请求"""
    warehouse_id: int
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    trans_type: str = Field(pattern="^(in|out|adjust)$", description="in=入库/out=出库/adjust=调整")
    qty: float = Field(gt=0, description="变动数量（正数，方向由trans_type决定）")
    unit_cost: Optional[float] = None
    operator: Optional[str] = None
    ref_doc_type: Optional[str] = None
    ref_doc_id: Optional[int] = None
    ref_doc_no: Optional[str] = None
    remark: Optional[str] = None
    set_min_stock: Optional[float] = None
    set_max_stock: Optional[float] = None
    set_reorder_point: Optional[float] = None


class InventoryStatsOut(BaseModel):
    """库存统计"""
    total_part_count: int = 0
    total_qty: float = 0.0
    total_value: float = 0.0
    low_stock_count: int = 0
    warehouse_count: int = 0
    low_stock_items: list[InventoryOut] = []


# ═══════════════ 库存流水 ═══════════════

class InventoryTransactionOut(BaseModel):
    id: int
    warehouse_id: int
    warehouse_name: Optional[str] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str
    trans_type: str
    qty: float
    balance_before: float
    balance_after: float
    ref_doc_type: Optional[str] = None
    ref_doc_id: Optional[int] = None
    ref_doc_no: Optional[str] = None
    operator: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class ReplenishmentSuggestionCreate(BaseModel):
    """创建补货建议"""
    warehouse_id: int
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    current_qty: float = 0.0
    reorder_point: float = 0.0
    min_stock: float = 0.0
    avg_daily_usage: float = 0.0
    suggested_qty: float = 0.0
    lead_time_days: int = 7
    unit_cost: float = 0.0
    remark: Optional[str] = None
    operator: Optional[str] = None


class ReplenishmentSuggestionUpdate(BaseModel):
    suggested_qty: Optional[float] = None
    lead_time_days: Optional[int] = None
    unit_cost: Optional[float] = None
    remark: Optional[str] = None


class ReplenishmentSuggestionOut(BaseModel):
    id: int
    warehouse_id: int
    warehouse_name: Optional[str] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str
    current_qty: float
    reorder_point: float
    min_stock: float
    avg_daily_usage: float
    suggested_qty: float
    lead_time_days: int
    expected_arrival: Optional[datetime] = None
    unit_cost: float
    total_cost: float
    status: str
    source: str
    remark: Optional[str] = None
    operator: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


class ReplenishmentStatsOut(BaseModel):
    """补货统计"""
    pending_count: int = 0
    approved_count: int = 0
    purchased_count: int = 0
    total_suggested_qty: float = 0.0
    total_cost: float = 0.0
    urgent_count: int = 0  # qty <= min_stock 的条数


# ═══════════════ 库位管理 ═══════════════


class StorageLocationCreate(BaseModel):
    warehouse_id: int
    code: str = Field(min_length=1, max_length=50)
    name: Optional[str] = None
    zone: Optional[str] = None
    row_label: Optional[str] = None
    shelf: Optional[str] = None
    bin: Optional[str] = None
    max_capacity: float = 0.0
    capacity_unit: str = "个"
    location_type: str = "storage"
    is_lockable: int = 0
    sort_order: int = 0
    remark: Optional[str] = None


class StorageLocationUpdate(BaseModel):
    name: Optional[str] = None
    zone: Optional[str] = None
    row_label: Optional[str] = None
    shelf: Optional[str] = None
    bin: Optional[str] = None
    max_capacity: Optional[float] = None
    current_occupied: Optional[float] = None
    capacity_unit: Optional[str] = None
    location_type: Optional[str] = None
    is_lockable: Optional[int] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    remark: Optional[str] = None


class StorageLocationOut(BaseModel):
    id: int
    warehouse_id: int
    warehouse_name: Optional[str] = None
    code: str
    name: Optional[str] = None
    zone: Optional[str] = None
    row_label: Optional[str] = None
    shelf: Optional[str] = None
    bin: Optional[str] = None
    max_capacity: float
    current_occupied: float
    capacity_unit: str
    location_type: str
    is_lockable: int
    status: str
    sort_order: int
    remark: Optional[str] = None
    is_deleted: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


class LocationStatsOut(BaseModel):
    total_locations: int = 0
    active_count: int = 0
    full_count: int = 0
    blocked_count: int = 0
    usage_rate: float = 0.0  # 综合利用率 %
    by_type: dict[str, int] = {}


class InventoryAlertCheckResult(BaseModel):
    """库存检查结果"""
    total_checked: int
    low_stock_count: int
    reorder_count: int
    alerts_created: int
    items: list[dict] = []


class InventoryTransactionFilter(BaseModel):
    warehouse_id: Optional[int] = None
    part_no: Optional[str] = None
    trans_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
