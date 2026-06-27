"""Phase 6 S2 — 认证中心 Schema"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


# ═══════════════ 区域1 — CertificationRequirement ═══════════════

class CertificationRequirementCreate(BaseModel):
    project_id: int
    target_market_id: int
    cert_type: str
    cert_body: Optional[str] = None
    is_mandatory: bool = True
    status: Optional[str] = None
    source_type: Optional[str] = None
    org_id: Optional[int] = None


class CertificationRequirementUpdate(BaseModel):
    cert_body: Optional[str] = None
    is_mandatory: Optional[bool] = None
    status: Optional[str] = None


class CertificationRequirementOut(BaseModel):
    id: int
    project_id: int
    target_market_id: int
    cert_type: str
    cert_body: Optional[str] = None
    is_mandatory: bool = True
    status: str
    source_type: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域2 — CertificationProject ═══════════════

class CertificationProjectCreate(BaseModel):
    code: Optional[str] = None
    name: str
    project_id: int
    target_market_id: int
    cert_types: Optional[str] = None
    status: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None


class CertificationProjectUpdate(BaseModel):
    name: Optional[str] = None
    cert_types: Optional[str] = None
    status: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    remark: Optional[str] = None


class CertificationProjectOut(BaseModel):
    id: int
    code: str
    name: str
    project_id: int
    target_market_id: int
    cert_types: Optional[str] = None
    status: str
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域3 — CertificationSample ═══════════════

class CertificationSampleCreate(BaseModel):
    cert_project_id: int
    prototype_id: int
    cert_type: str
    sample_no: Optional[str] = None
    status: Optional[str] = None
    submitted_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None


class CertificationSampleUpdate(BaseModel):
    cert_type: Optional[str] = None
    status: Optional[str] = None
    submitted_date: Optional[date] = None
    remark: Optional[str] = None


class CertificationSampleOut(BaseModel):
    id: int
    cert_project_id: int
    prototype_id: int
    cert_type: str
    sample_no: str
    status: str
    submitted_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域4 — CertificationExecution ═══════════════

class CertificationExecutionCreate(BaseModel):
    cert_sample_id: int
    lab: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    result_summary: Optional[str] = None
    org_id: Optional[int] = None


class CertificationExecutionUpdate(BaseModel):
    lab: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    result_summary: Optional[str] = None


class CertificationExecutionOut(BaseModel):
    id: int
    cert_sample_id: int
    lab: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    result_summary: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域5 — CertificationResult ═══════════════

class CertificationResultCreate(BaseModel):
    cert_execution_id: int
    status: Optional[str] = None
    result_date: Optional[date] = None
    summary: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None


class CertificationResultUpdate(BaseModel):
    status: Optional[str] = None
    result_date: Optional[date] = None
    summary: Optional[str] = None
    attachments: Optional[str] = None


class CertificationResultOut(BaseModel):
    id: int
    cert_execution_id: int
    status: str
    result_date: Optional[date] = None
    summary: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域6 — Certificate ═══════════════

class CertificateCreate(BaseModel):
    cert_result_id: int
    cert_no: str
    cert_type: str
    issuing_body: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    attachments: Optional[str] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None


class CertificateUpdate(BaseModel):
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    attachments: Optional[str] = None
    remark: Optional[str] = None


class CertificateOut(BaseModel):
    id: int
    cert_result_id: int
    cert_no: str
    cert_type: str
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    attachments: Optional[str] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域7 — CertificateVersion ═══════════════

class CertificateVersionCreate(BaseModel):
    certificate_id: int
    version_no: str
    cert_no: str
    issuing_body: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    change_reason: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None


class CertificateVersionOut(BaseModel):
    id: int
    certificate_id: int
    version_no: str
    cert_no: str
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    change_reason: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域8 — CertificationGateRule ═══════════════

class CertificationGateRuleCreate(BaseModel):
    name: str
    gate_code: str
    target_market_id: Optional[int] = None
    cert_type: str
    is_required: bool = True
    auto_block: bool = False
    priority: int = 100
    status: Optional[str] = None
    org_id: Optional[int] = None


class CertificationGateRuleUpdate(BaseModel):
    name: Optional[str] = None
    gate_code: Optional[str] = None
    target_market_id: Optional[int] = None
    cert_type: Optional[str] = None
    is_required: Optional[bool] = None
    auto_block: Optional[bool] = None
    priority: Optional[int] = None
    status: Optional[str] = None


class CertificationGateRuleOut(BaseModel):
    id: int
    name: str
    gate_code: str
    target_market_id: Optional[int] = None
    cert_type: str
    is_required: bool = True
    auto_block: bool = False
    priority: int = 100
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域9 — ChangeImpactRule ═══════════════

class ChangeImpactRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_value: str
    affected_cert_types: str
    impact_level: str
    is_active: bool = True
    org_id: Optional[int] = None


class ChangeImpactRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    affected_cert_types: Optional[str] = None
    impact_level: Optional[str] = None
    is_active: Optional[bool] = None


class ChangeImpactRuleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_value: str
    affected_cert_types: str
    impact_level: str
    is_active: bool = True
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域10 — ChangeImpactRecord (只读) ═══════════════

class ChangeImpactRecordOut(BaseModel):
    id: int
    ecr_id: Optional[int] = None
    prototype_id: Optional[int] = None
    changed_part: Optional[str] = None
    matched_rule_id: Optional[int] = None
    impact_level: str
    affected_cert_types: str
    analysis_detail: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
