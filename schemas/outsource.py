"""外协管理模块 — Pydantic Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import date, datetime


# ═══════════════ 外协厂商 ═══════════════

class OutsourcePartnerCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    partner_type: str = "other"
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    business_scope: Optional[str] = None
    qualification_level: str = "B"
    rating: Optional[int] = None
    remark: Optional[str] = None


class OutsourcePartnerUpdate(BaseModel):
    name: Optional[str] = None
    partner_type: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    business_scope: Optional[str] = None
    qualification_level: Optional[str] = None
    rating: Optional[int] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class OutsourcePartnerOut(BaseModel):
    id: int
    code: str
    name: str
    partner_type: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    business_scope: Optional[str] = None
    qualification_level: Optional[str] = None
    rating: Optional[int] = None
    status: str
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    orders_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class OutsourcePartnerListOut(BaseModel):
    items: list[OutsourcePartnerOut]
    total: int


# ═══════════════ 外协订单 ═══════════════

class OutsourceOrderItemBase(BaseModel):
    part_no: str = Field(min_length=1, max_length=50)
    part_name: Optional[str] = None
    spec: Optional[str] = None
    quantity: float = 1.0
    unit: str = "个"
    unit_price: float = 0.0
    total_price: float = 0.0
    delivery_date: Optional[date] = None
    received_qty: float = 0.0
    remark: Optional[str] = None
    sort_order: int = 0


class OutsourceOrderItemOut(OutsourceOrderItemBase):
    id: int
    order_id: int
    org_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OutsourceOrderCreate(BaseModel):
    partner_id: int
    title: str = Field(min_length=1, max_length=300)
    project_id: Optional[int] = None
    order_type: str = "part"
    quantity: int = 1
    unit: str = "批"
    unit_price: float = 0.0
    total_amount: float = 0.0
    delivery_date: Optional[date] = None
    priority: str = "normal"
    technical_requirements: Optional[str] = None
    quality_requirements: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    items: list[OutsourceOrderItemBase] = []


class OutsourceOrderUpdate(BaseModel):
    title: Optional[str] = None
    partner_id: Optional[int] = None
    project_id: Optional[int] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    technical_requirements: Optional[str] = None
    quality_requirements: Optional[str] = None
    remark: Optional[str] = None


class OutsourceOrderOut(BaseModel):
    id: int
    order_no: str
    partner_id: int
    project_id: Optional[int] = None
    title: str
    order_type: str
    quantity: int
    unit: str
    unit_price: float
    total_amount: float
    delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    status: str
    priority: str
    technical_requirements: Optional[str] = None
    quality_requirements: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    attachment_urls: Optional[Any] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    partner_name: str = ""
    items: list[OutsourceOrderItemOut] = []
    quality_records_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class OutsourceOrderListOut(BaseModel):
    items: list[OutsourceOrderOut]
    total: int


# ═══════════════ 外协质检 ═══════════════

class OutsourceQualityRecordCreate(BaseModel):
    order_id: int
    inspect_type: str = "incoming"
    inspect_date: date
    inspector: Optional[str] = None
    sample_qty: int = 0
    defect_qty: int = 0
    result: str = "pass"
    defect_description: Optional[str] = None
    conclusion: Optional[str] = None


class OutsourceQualityRecordUpdate(BaseModel):
    inspect_type: Optional[str] = None
    inspect_date: Optional[date] = None
    inspector: Optional[str] = None
    sample_qty: Optional[int] = None
    defect_qty: Optional[int] = None
    result: Optional[str] = None
    defect_description: Optional[str] = None
    conclusion: Optional[str] = None


class OutsourceQualityRecordOut(BaseModel):
    id: int
    order_id: int
    inspect_type: str
    inspect_date: date
    inspector: Optional[str] = None
    sample_qty: int
    defect_qty: int
    result: str
    defect_description: Optional[str] = None
    conclusion: Optional[str] = None
    attachments: Optional[Any] = None
    org_id: Optional[int] = None
    created_at: datetime
    order_title: str = ""
    model_config = ConfigDict(from_attributes=True)


class OutsourceQualityRecordListOut(BaseModel):
    items: list[OutsourceQualityRecordOut]
    total: int
