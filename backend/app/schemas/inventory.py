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


class InventoryTransactionFilter(BaseModel):
    warehouse_id: Optional[int] = None
    part_no: Optional[str] = None
    trans_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
