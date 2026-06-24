"""安规管理模块 — Pydantic Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import date, datetime


# ═══════════════ 安全标准库 ═══════════════

class SafetyStandardCreate(BaseModel):
    standard_code: str = Field(min_length=1, max_length=100)
    standard_name_cn: str = Field(min_length=1, max_length=300)
    standard_name_en: Optional[str] = None
    issuing_body: Optional[str] = None
    applicable_market: Optional[str] = None
    standard_type: str = "safety"
    version: Optional[str] = "V1.0"
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    abolish_date: Optional[date] = None
    summary: Optional[str] = None
    attachment_url: Optional[str] = None
    status: str = "active"


class SafetyStandardUpdate(BaseModel):
    standard_code: Optional[str] = None
    standard_name_cn: Optional[str] = None
    standard_name_en: Optional[str] = None
    issuing_body: Optional[str] = None
    applicable_market: Optional[str] = None
    standard_type: Optional[str] = None
    version: Optional[str] = None
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    abolish_date: Optional[date] = None
    summary: Optional[str] = None
    attachment_url: Optional[str] = None
    status: Optional[str] = None


class SafetyStandardOut(BaseModel):
    id: int
    standard_code: str
    standard_name_cn: str
    standard_name_en: Optional[str] = None
    issuing_body: Optional[str] = None
    applicable_market: Optional[str] = None
    standard_type: str
    version: Optional[str] = None
    publish_date: Optional[date] = None
    effective_date: Optional[date] = None
    abolish_date: Optional[date] = None
    summary: Optional[str] = None
    attachment_url: Optional[str] = None
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    inspection_items_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class SafetyStandardListOut(BaseModel):
    items: list[SafetyStandardOut]
    total: int


# ═══════════════ 安规检测项 ═══════════════

class SafetyInspectionItemCreate(BaseModel):
    standard_id: int
    item_code: str = Field(min_length=1, max_length=100)
    item_name: str = Field(min_length=1, max_length=300)
    inspection_category: Optional[str] = None
    param_name: Optional[str] = None
    standard_value_min: Optional[float] = None
    standard_value_max: Optional[float] = None
    standard_value_nominal: Optional[str] = None
    unit: Optional[str] = None
    applicable_product_type: Optional[str] = None
    test_method: Optional[str] = None
    reference_clause: Optional[str] = None
    sort_order: int = 0
    status: str = "active"


class SafetyInspectionItemUpdate(BaseModel):
    standard_id: Optional[int] = None
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    inspection_category: Optional[str] = None
    param_name: Optional[str] = None
    standard_value_min: Optional[float] = None
    standard_value_max: Optional[float] = None
    standard_value_nominal: Optional[str] = None
    unit: Optional[str] = None
    applicable_product_type: Optional[str] = None
    test_method: Optional[str] = None
    reference_clause: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None


class SafetyInspectionItemOut(BaseModel):
    id: int
    standard_id: int
    item_code: str
    item_name: str
    inspection_category: Optional[str] = None
    param_name: Optional[str] = None
    standard_value_min: Optional[float] = None
    standard_value_max: Optional[float] = None
    standard_value_nominal: Optional[str] = None
    unit: Optional[str] = None
    applicable_product_type: Optional[str] = None
    test_method: Optional[str] = None
    reference_clause: Optional[str] = None
    sort_order: int = 0
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    standard_code: str = ""
    model_config = ConfigDict(from_attributes=True)


class SafetyInspectionItemListOut(BaseModel):
    items: list[SafetyInspectionItemOut]
    total: int


# ═══════════════ 供应商安规资质 ═══════════════

class SupplierSafetyQualificationCreate(BaseModel):
    supplier_id: int
    qualification_type: str = Field(min_length=1, max_length=100)
    cert_no: Optional[str] = None
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    attachments: Optional[Any] = None
    status: str = "active"
    audit_status: str = "pending"
    audit_comment: Optional[str] = None


class SupplierSafetyQualificationUpdate(BaseModel):
    qualification_type: Optional[str] = None
    cert_no: Optional[str] = None
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    attachments: Optional[Any] = None
    status: Optional[str] = None
    audit_status: Optional[str] = None
    audit_comment: Optional[str] = None


class SupplierSafetyQualificationOut(BaseModel):
    id: int
    supplier_id: int
    qualification_type: str
    cert_no: Optional[str] = None
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    attachments: Optional[Any] = None
    status: str
    audit_status: str
    audit_comment: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    audit_records: list["SafetyAuditRecordOut"] = []
    supplier_name: str = ""
    model_config = ConfigDict(from_attributes=True)


class SupplierSafetyQualificationListOut(BaseModel):
    items: list[SupplierSafetyQualificationOut]
    total: int


class SafetyAuditRecordCreate(BaseModel):
    qualification_id: int
    audit_date: date
    auditor: Optional[str] = None
    result: str = "pass"
    findings: Optional[Any] = None
    attachments: Optional[Any] = None
    next_audit_date: Optional[date] = None


class SafetyAuditRecordUpdate(BaseModel):
    audit_date: Optional[date] = None
    auditor: Optional[str] = None
    result: Optional[str] = None
    findings: Optional[Any] = None
    attachments: Optional[Any] = None
    next_audit_date: Optional[date] = None


class SafetyAuditRecordOut(BaseModel):
    id: int
    qualification_id: int
    audit_date: date
    auditor: Optional[str] = None
    result: str
    findings: Optional[Any] = None
    attachments: Optional[Any] = None
    next_audit_date: Optional[date] = None
    org_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 安规预警展示 ═══════════════

class SafetyAlertItem(BaseModel):
    """安规预警条目"""
    alert_type: str  # cert_expiry / qual_expiry / standard_change
    title: str
    description: str
    severity: str  # critical / warning / info
    target_type: str
    target_id: int
    expiry_date: Optional[date] = None
    days_remaining: Optional[int] = None


class SafetyAlertListOut(BaseModel):
    items: list[SafetyAlertItem]
    total: int
