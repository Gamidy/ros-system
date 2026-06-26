"""Phase 6 S1 — 验证需求/测试执行/门控规则/目标市场 Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date


# ═══════════════════════════════════════════
# 区域1 — VerificationRequirement
# ═══════════════════════════════════════════

class VerificationRequirementCreate(BaseModel):
    title: str
    category: str
    target_value: Optional[str] = None
    unit: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None
    source_detail: Optional[str] = None
    project_id: Optional[int] = None
    product_plan_id: Optional[int] = None
    gate_code: Optional[str] = None
    remark: Optional[str] = None


class VerificationRequirementOut(VerificationRequirementCreate):
    id: int
    vr_code: str
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class VerificationRequirementGenerateRequest(BaseModel):
    product_plan_id: int
    auto_generate: bool = True


# ═══════════════════════════════════════════
# 区域2 — TestExecution
# ═══════════════════════════════════════════

class TestExecutionCreate(BaseModel):
    test_request_id: int
    lab: Optional[str] = None
    equipment: Optional[str] = None
    operator: Optional[str] = None
    start_time: Optional[datetime] = None
    notes: Optional[str] = None


class TestExecutionOut(TestExecutionCreate):
    id: int
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════
# 区域3 — GateRule
# ═══════════════════════════════════════════

class GateRuleItemCreate(BaseModel):
    required_vr_category: str
    required_prototype_type: Optional[str] = None
    is_required: bool = True
    sort_order: int = 0


class GateRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    product_line: Optional[str] = None
    customer: Optional[str] = None
    gate_code: str
    all_pass: bool = True
    auto_block: bool = False
    priority: int = 100
    items: list[GateRuleItemCreate] = []


class GateRuleItemOut(GateRuleItemCreate):
    id: int
    rule_id: int
    model_config = ConfigDict(from_attributes=True)


class GateRuleOut(GateRuleCreate):
    id: int
    status: str
    created_by: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: list[GateRuleItemOut] = []
    model_config = ConfigDict(from_attributes=True)


class GateRuleEvalRequest(BaseModel):
    project_id: int
    gate_code: str
    product_line: Optional[str] = None
    customer: Optional[str] = None


# ═══════════════════════════════════════════
# 区域4 — TargetMarket
# ═══════════════════════════════════════════

class RequiredTestCreate(BaseModel):
    test_category: str
    standard: Optional[str] = None
    is_required: bool = True
    sort_order: int = 0


class RequiredCertificationCreate(BaseModel):
    cert_type: str
    cert_body: Optional[str] = None
    is_mandatory: bool = True
    sort_order: int = 0


class RequiredStandardCreate(BaseModel):
    standard_code: str
    standard_name: Optional[str] = None
    is_core: bool = True
    sort_order: int = 0


class TargetMarketCreate(BaseModel):
    market_code: str
    market_name: str
    description: Optional[str] = None


class RequiredTestOut(RequiredTestCreate):
    id: int
    target_market_id: int
    model_config = ConfigDict(from_attributes=True)


class RequiredCertificationOut(RequiredCertificationCreate):
    id: int
    target_market_id: int
    model_config = ConfigDict(from_attributes=True)


class RequiredStandardOut(RequiredStandardCreate):
    id: int
    target_market_id: int
    model_config = ConfigDict(from_attributes=True)


class TargetMarketOut(TargetMarketCreate):
    id: int
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    required_tests: list[RequiredTestOut] = []
    required_certifications: list[RequiredCertificationOut] = []
    required_standards: list[RequiredStandardOut] = []
    model_config = ConfigDict(from_attributes=True)
