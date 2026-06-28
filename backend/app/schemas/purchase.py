"""采购管理 — Pydantic Schema"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════ 供应商管理 ═══════════════


class SupplierCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    bank_info: Optional[str] = None
    status: str = "active"
    overall_score: float = 0
    business_license: Optional[str] = None
    cert_iso: int = 0
    cert_rohs: int = 0
    cert_ul: int = 0
    remark: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    bank_info: Optional[str] = None
    status: Optional[str] = None
    overall_score: Optional[float] = None
    business_license: Optional[str] = None
    cert_iso: Optional[int] = None
    cert_rohs: Optional[int] = None
    cert_ul: Optional[int] = None
    remark: Optional[str] = None


class SupplierOut(SupplierCreate):
    id: int
    is_deleted: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


# ═══════════════ 供应商评估 ═══════════════


class EvaluationCreate(BaseModel):
    dimension: str
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(1.0, ge=0, le=1)
    comment: Optional[str] = None
    evaluator: Optional[str] = None


class EvaluationOut(BaseModel):
    id: int
    supplier_id: int
    dimension: str
    dimension_label: str = ""
    score: float
    weight: float
    comment: Optional[str] = None
    evaluator: Optional[str] = None
    evaluated_at: datetime
    class Config: from_attributes = True


class SupplierStatsOut(BaseModel):
    total_count: int = 0
    qualified_count: int = 0
    active_count: int = 0
    suspended_count: int = 0
    blacklisted_count: int = 0
    avg_score: float = 0
    low_score_count: int = 0
    category_count: int = 0


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


# ═══════════════ 采购收货 ═══════════════


class ReceiptItemCreate(BaseModel):
    order_item_id: Optional[int] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    ordered_qty: float = 0
    received_qty: float = 0
    unit_price: float = 0


class ReceiptCreate(BaseModel):
    order_id: int
    warehouse: Optional[str] = None
    location: Optional[str] = None
    remark: Optional[str] = None
    items: list[ReceiptItemCreate] = []


class ReceiptItemOut(BaseModel):
    id: int
    receipt_id: int
    order_item_id: Optional[int] = None
    part_no: str
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str
    ordered_qty: float
    received_qty: float
    accepted_qty: float
    rejected_qty: float
    unit_price: float
    total_price: float
    remark: Optional[str] = None
    class Config: from_attributes = True


class ReceiptOut(BaseModel):
    id: int
    receipt_no: str
    order_id: int
    supplier_name: str
    supplier_code: str
    received_date: Optional[datetime] = None
    warehouse: Optional[str] = None
    location: Optional[str] = None
    status: str
    total_qty: float
    total_amount: float
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: list[ReceiptItemOut] = []
    class Config: from_attributes = True


# ═══════════════ 来料检验 ═══════════════


class InspectionCreate(BaseModel):
    receipt_id: int
    receipt_item_id: Optional[int] = None
    part_no: str
    sample_qty: int = 0
    defect_qty: int = 0
    defect_desc: Optional[str] = None
    result: str = "pass"
    inspector: Optional[str] = None
    remark: Optional[str] = None


class InspectionOut(BaseModel):
    id: int
    receipt_id: int
    receipt_item_id: Optional[int] = None
    part_no: str
    sample_qty: int
    defect_qty: int
    defect_desc: Optional[str] = None
    result: str
    inspector: Optional[str] = None
    remark: Optional[str] = None
    inspected_at: datetime
    class Config: from_attributes = True


# ═══════════════ 采购质检统计 ═══════════════


class SupplierQualityItem(BaseModel):
    """供应商质量统计"""
    supplier_name: str = ""
    supplier_code: str = ""
    total_inspections: int = 0
    pass_count: int = 0
    concession_count: int = 0
    reject_count: int = 0
    pass_rate: float = 0.0


class QualityTrendItem(BaseModel):
    """质量趋势（按月份）"""
    month: str = ""
    total: int = 0
    pass_count: int = 0
    reject_count: int = 0
    pass_rate: float = 0.0


class DefectTypeItem(BaseModel):
    """缺陷分类统计"""
    defect_desc: str = ""
    count: int = 0


class QualityStatsOut(BaseModel):
    """采购质检整体统计"""
    total_inspections: int = 0
    pass_rate: float = 0.0
    concession_rate: float = 0.0
    reject_rate: float = 0.0
    month_total: int = 0
    month_pass_rate: float = 0.0
    by_supplier: list[SupplierQualityItem] = []
    trend: list[QualityTrendItem] = []
    top_defects: list[DefectTypeItem] = []
    recent_rejects: list[dict] = []
