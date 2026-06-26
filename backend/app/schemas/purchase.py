"""采购管理 — Pydantic Schema"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════ 供应商管理 ═══════════════


class SupplierCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    bank_info: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    bank_info: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class SupplierOut(SupplierCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


# ═══════════════ 采购订单 ═══════════════


class PurchaseOrderItemCreate(BaseModel):
    part_no: str = Field(min_length=1, max_length=50)
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    quantity: float = 1.0
    unit_price: float = 0.0
    total_price: float = 0.0
    delivery_date: Optional[date] = None
    received_qty: float = 0.0
    remark: Optional[str] = None


class PurchaseOrderItemUpdate(BaseModel):
    part_no: Optional[str] = None
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    delivery_date: Optional[date] = None
    received_qty: Optional[float] = None
    remark: Optional[str] = None


class PurchaseOrderItemOut(PurchaseOrderItemCreate):
    id: int
    order_id: int
    created_at: datetime
    class Config: from_attributes = True


class PurchaseOrderCreate(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=200)
    supplier_code: str = Field(min_length=1, max_length=50)
    total_amount: float = 0.0
    status: str = "draft"
    requester: str = Field(min_length=1, max_length=100)
    remark: Optional[str] = None
    items: list[PurchaseOrderItemCreate] = []


class PurchaseOrderStatusUpdate(BaseModel):
    status: str


class PurchaseOrderOut(BaseModel):
    id: int
    order_no: str
    supplier_name: str
    supplier_code: str
    total_amount: float
    status: str
    requester: str
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True


class PurchaseOrderDetailOut(PurchaseOrderOut):
    items: list[PurchaseOrderItemOut] = []
    class Config: from_attributes = True


# ═══════════════ 采购看板 ═══════════════


class PurchaseDashboardOut(BaseModel):
    pending_approval: int = 0
    month_total_amount: float = 0.0
    month_order_count: int = 0
    pending_received: int = 0
    total_orders: int = 0
    total_suppliers: int = 0
    status_breakdown: dict[str, int] = {}
