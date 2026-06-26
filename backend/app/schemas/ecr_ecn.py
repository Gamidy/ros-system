"""ECR/ECN 工程变更 — Pydantic Schema（旧版）"""

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ═══════════════ ECR ═══════════════

class ECRCreate(BaseModel):
    title: str
    product_code: Optional[str] = None
    change_type: str
    trigger: Optional[str] = None
    description: Optional[str] = None
    impact_analysis: Optional[str] = None


class ECROut(ECRCreate):
    id: int
    ecr_no: str
    status: str
    submitted_by: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ ECN ═══════════════

class ECNCreate(BaseModel):
    ecr_id: Optional[int] = None
    title: str
    product_code: Optional[str] = None
    change_scope: Optional[str] = None
    bom_changes: Optional[str] = None
    cdf_impact: bool = False
    certification_impact: bool = False
    effective_date: Optional[date] = None


class ECNOut(ECNCreate):
    id: int
    ecn_no: str
    status: str
    created_at: datetime
    class Config: from_attributes = True
