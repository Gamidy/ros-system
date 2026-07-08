"""盘点管理 — Pydantic Schema"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InventoryCountItemCreate(BaseModel):
    inventory_id: Optional[int] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    system_qty: float = 0
    actual_qty: float = 0
    remark: Optional[str] = None


class InventoryCountCreate(BaseModel):
    warehouse_id: int
    count_type: str = "partial"
    counted_by: Optional[str] = None
    remark: Optional[str] = None
    items: list[InventoryCountItemCreate] = []


class InventoryCountItemOut(BaseModel):
    id: int
    count_id: int
    inventory_id: Optional[int] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str
    system_qty: float
    actual_qty: float
    diff_qty: float
    unit_cost: float
    diff_value: float
    status: str
    remark: Optional[str] = None
    adjusted_at: Optional[datetime] = None
    class Config: from_attributes = True


class InventoryCountOut(BaseModel):
    id: int
    count_no: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    count_type: str
    status: str
    total_items: int
    matched_count: int
    discrepancy_count: int
    total_discrepancy_value: float
    count_date: Optional[datetime] = None
    counted_by: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: list[InventoryCountItemOut] = []
    class Config: from_attributes = True


class InventoryCountListItem(BaseModel):
    id: int
    count_no: str
    warehouse_name: Optional[str] = None
    count_type: str
    status: str
    total_items: int
    matched_count: int
    discrepancy_count: int
    total_discrepancy_value: float
    count_date: Optional[datetime] = None
    counted_by: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class CountItemUpdate(BaseModel):
    actual_qty: float
    remark: Optional[str] = None


class CountStatsOut(BaseModel):
    total_counts: int = 0
    pending_count: int = 0
    completed_count: int = 0
    discrepancy_count: int = 0
    total_discrepancy_value: float = 0.0
