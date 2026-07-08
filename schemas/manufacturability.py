"""DFM可制造性分析模块 — Pydantic Schema"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Any
from datetime import datetime

from app.core.constants import VALID_PRODUCT_TYPES


def _validate_product_type(v):
    """Validate product_type is one of the allowed values."""
    if v is not None and v not in VALID_PRODUCT_TYPES:
        raise ValueError(f"不支持的产品类型: {v}")
    return v


# ═══════════════ DFM检查项模板 ═══════════════

class DFMChecklistCreate(BaseModel):
    item_code: str = Field(min_length=1, max_length=100)
    item_name: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    dfm_category: str = "structural"
    severity: str = "major"
    applicable_product_types: Optional[str] = None
    reference_standard: Optional[str] = None
    check_method: Optional[str] = None
    weight: Optional[float] = 1.0
    sort_order: int = 0
    status: str = "active"


class DFMChecklistUpdate(BaseModel):
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    description: Optional[str] = None
    dfm_category: Optional[str] = None
    severity: Optional[str] = None
    applicable_product_types: Optional[str] = None
    reference_standard: Optional[str] = None
    check_method: Optional[str] = None
    weight: Optional[float] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None


class DFMChecklistOut(BaseModel):
    id: int
    item_code: str
    item_name: str
    description: Optional[str] = None
    dfm_category: str
    severity: str
    applicable_product_types: Optional[str] = None
    reference_standard: Optional[str] = None
    check_method: Optional[str] = None
    weight: Optional[float] = None
    sort_order: int = 0
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DFMChecklistListOut(BaseModel):
    items: list[DFMChecklistOut]
    total: int


# ═══════════════ DFM分析报告 ═══════════════

class DFMReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    project_id: Optional[int] = None
    prototype_id: Optional[int] = None
    product_type: Optional[str] = None
    version: Optional[str] = "V1.0"
    summary: Optional[str] = None
    created_by: Optional[str] = None

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        return _validate_product_type(v)


class DFMReportUpdate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None
    prototype_id: Optional[int] = None
    product_type: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        return _validate_product_type(v)


class DFMReportItemOut(BaseModel):
    id: int
    report_id: int
    checklist_id: Optional[int] = None
    issue_desc: str
    dfm_category: Optional[str] = None
    severity: str
    suggestion: Optional[str] = None
    responsible_person: Optional[str] = None
    status: str
    score: Optional[float] = None
    attachments: Optional[Any] = None
    sort_order: int = 0
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DFMReportOut(BaseModel):
    id: int
    report_no: str
    title: str
    project_id: Optional[int] = None
    prototype_id: Optional[int] = None
    product_type: Optional[str] = None
    version: Optional[str] = None
    status: str
    total_score: Optional[float] = None
    summary: Optional[str] = None
    created_by: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: list[DFMReportItemOut] = []
    model_config = ConfigDict(from_attributes=True)

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        return _validate_product_type(v)


class DFMReportListOut(BaseModel):
    items: list[DFMReportOut]
    total: int


# ═══════════════ DFM报告问题项 ═══════════════

class DFMReportItemCreate(BaseModel):
    report_id: int
    checklist_id: Optional[int] = None
    issue_desc: str = Field(min_length=1)
    dfm_category: Optional[str] = None
    severity: str = "major"
    suggestion: Optional[str] = None
    responsible_person: Optional[str] = None
    score: Optional[float] = None
    attachments: Optional[Any] = None
    sort_order: int = 0


class DFMReportItemUpdate(BaseModel):
    issue_desc: Optional[str] = None
    dfm_category: Optional[str] = None
    severity: Optional[str] = None
    suggestion: Optional[str] = None
    responsible_person: Optional[str] = None
    status: Optional[str] = None
    score: Optional[float] = None
    attachments: Optional[Any] = None
    sort_order: Optional[int] = None


# ═══════════════ 评分权重配置 ═══════════════

class DFMScoreWeightCreate(BaseModel):
    product_type: str = Field(min_length=1, max_length=100)
    dfm_category: str
    weight: float = Field(ge=0, le=1)

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        return _validate_product_type(v)


class DFMScoreWeightUpdate(BaseModel):
    weight: Optional[float] = Field(None, ge=0, le=1)


class DFMScoreWeightOut(BaseModel):
    id: int
    product_type: str
    dfm_category: str
    weight: float
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        return _validate_product_type(v)


class DFMScoreWeightListOut(BaseModel):
    items: list[DFMScoreWeightOut]
    total: int


# ═══════════════ 评分计算结果 ═══════════════

class DFMScoreResult(BaseModel):
    """DFM评分计算结果"""
    total_score: float
    category_scores: dict[str, dict]  # category: {score, max, weight}
    item_count: int
    critical_count: int
    major_count: int
    minor_count: int
