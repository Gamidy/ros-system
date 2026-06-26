"""认证/样机/品质管理 — Pydantic Schema"""

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ═══════════════ 认证管理 ═══════════════

class CertificationCreate(BaseModel):
    product_code: str
    cert_type: str
    target_market: str
    cert_body: Optional[str] = None
    planned_date: Optional[date] = None
    cdf_doc_ref: Optional[str] = None
    remark: Optional[str] = None


class CertificationOut(CertificationCreate):
    id: int
    cert_no: str
    status: str
    submit_date: Optional[date] = None
    approved_date: Optional[date] = None
    expiry_date: Optional[date] = None
    result: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 样机管理 ═══════════════

class PrototypeCreate(BaseModel):
    product_code: str
    project_code: Optional[str] = None
    proto_type: str
    stage: Optional[str] = None
    quantity: int = 1
    remark: Optional[str] = None
    version: Optional[str] = None
    project_id: Optional[int] = None
    parent_prototype_id: Optional[int] = None
    bom_version: Optional[str] = None
    firmware_version: Optional[str] = None


class PrototypeOut(PrototypeCreate):
    id: int
    proto_no: str
    status: str
    material_status: Optional[str] = None
    produced_date: Optional[date] = None
    test_date: Optional[date] = None
    result: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 品质问题 ═══════════════

class QualityIssueCreate(BaseModel):
    title: str
    product_code: Optional[str] = None
    project_code: Optional[str] = None
    issue_source: Optional[str] = None
    severity: str = "B"
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    target_date: Optional[date] = None


class QualityIssueOut(QualityIssueCreate):
    id: int
    issue_no: str
    status: str
    root_cause: Optional[str] = None
    solution: Optional[str] = None
    closed_date: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True
