"""8D报告管理 — Pydantic Schema"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime


class EightDReportCreate(BaseModel):
    report_no: str = Field(min_length=1, max_length=50)
    issue_title: str = Field(min_length=1, max_length=300)
    issue_desc: Optional[str] = None
    severity: str = "C"
    product_info: Optional[str] = None
    d1_team: Optional[str] = None
    d2_problem_desc: Optional[str] = None
    d3_containment: Optional[str] = None
    d4_root_cause: Optional[str] = None
    d5_corrective_action: Optional[str] = None
    d6_implement: Optional[str] = None
    d7_prevention: Optional[str] = None
    d8_closure: Optional[str] = None
    responsible_person: Optional[str] = None
    target_date: Optional[date] = None
    remark: Optional[str] = None


class EightDReportUpdate(BaseModel):
    issue_title: Optional[str] = None
    issue_desc: Optional[str] = None
    severity: Optional[str] = None
    product_info: Optional[str] = None
    d1_team: Optional[str] = None
    d2_problem_desc: Optional[str] = None
    d3_containment: Optional[str] = None
    d4_root_cause: Optional[str] = None
    d5_corrective_action: Optional[str] = None
    d6_implement: Optional[str] = None
    d7_prevention: Optional[str] = None
    d8_closure: Optional[str] = None
    responsible_person: Optional[str] = None
    target_date: Optional[date] = None
    remark: Optional[str] = None


class EightDReportOut(BaseModel):
    id: int
    report_no: str
    issue_title: str
    issue_desc: Optional[str] = None
    severity: str
    product_info: Optional[str] = None
    d1_team: Optional[str] = None
    d2_problem_desc: Optional[str] = None
    d3_containment: Optional[str] = None
    d4_root_cause: Optional[str] = None
    d5_corrective_action: Optional[str] = None
    d6_implement: Optional[str] = None
    d7_prevention: Optional[str] = None
    d8_closure: Optional[str] = None
    status: str
    responsible_person: Optional[str] = None
    target_date: Optional[date] = None
    closed_date: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EightDReportListOut(BaseModel):
    items: list[EightDReportOut]
    total: int


class EightDReportStatusUpdate(BaseModel):
    status: str = Field(description="目标状态: open/analysis/containment/corrective/verify/closed")
