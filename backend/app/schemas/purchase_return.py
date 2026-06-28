"""采购退货管理 — Pydantic Schema"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════ 退货明细 ═══════════════


class ReturnItemCreate(BaseModel):
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    return_qty: float = Field(gt=0)
    unit_price: float = 0.0
    inspection_item_id: Optional[int] = None
    defect_type: Optional[str] = None
    defect_desc: Optional[str] = None
    disposal: str = "return"
    remark: Optional[str] = None


class ReturnItemOut(BaseModel):
    id: int
    return_id: int
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str
    return_qty: float
    unit_price: float
    total_price: float
    inspection_item_id: Optional[int] = None
    defect_type: Optional[str] = None
    defect_desc: Optional[str] = None
    disposal: str
    remark: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 退货单 ═══════════════


class ReturnCreate(BaseModel):
    source_type: str = Field(pattern="^(inspection|receipt|manual)$")
    source_id: Optional[int] = None
    source_no: Optional[str] = None
    supplier_name: str
    supplier_code: str
    order_id: Optional[int] = None
    order_no: Optional[str] = None
    return_reason: str = Field(pattern="^(quality|overdue|damaged|other)$")
    reason_detail: Optional[str] = None
    responsibility: str = "supplier"
    logistics_company: Optional[str] = None
    logistics_no: Optional[str] = None
    remark: Optional[str] = None
    created_by: str = "系统"
    items: list[ReturnItemCreate] = []


class ReturnUpdate(BaseModel):
    return_reason: Optional[str] = None
    reason_detail: Optional[str] = None
    responsibility: Optional[str] = None
    logistics_company: Optional[str] = None
    logistics_no: Optional[str] = None
    refund_amount: Optional[float] = None
    refund_date: Optional[datetime] = None
    refund_method: Optional[str] = None
    remark: Optional[str] = None


class ReturnOut(BaseModel):
    id: int
    return_no: str
    source_type: str
    source_id: Optional[int] = None
    source_no: Optional[str] = None
    supplier_name: str
    supplier_code: str
    order_id: Optional[int] = None
    order_no: Optional[str] = None
    return_date: datetime
    total_qty: float
    total_amount: float
    return_reason: str
    reason_detail: Optional[str] = None
    responsibility: str
    logistics_company: Optional[str] = None
    logistics_no: Optional[str] = None
    refund_amount: float
    refund_date: Optional[datetime] = None
    refund_method: Optional[str] = None
    status: str
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: list[ReturnItemOut] = []
    class Config: from_attributes = True


class ReturnStatsOut(BaseModel):
    """退货统计"""
    total_count: int = 0
    draft_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    returned_count: int = 0
    refunded_count: int = 0
    cancelled_count: int = 0
    total_return_qty: float = 0.0
    total_return_amount: float = 0.0
    pending_refund_amount: float = 0.0
