"""测试与MQ验证管理 — Pydantic Schema"""

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ═══════════════ 测试结果 ═══════════════

class TestResultCreate(BaseModel):
    item_name: str
    standard_value: Optional[str] = None
    actual_value: Optional[str] = None
    is_pass: Optional[bool] = None
    # Phase 6 增强字段
    prototype_id: Optional[int] = None
    execution_id: Optional[int] = None
    result: Optional[str] = None
    judgment_data: Optional[str] = None
    remark: Optional[str] = None
    tested_by: Optional[str] = None


class TestResultOut(TestResultCreate):
    id: int
    test_request_id: int
    tested_at: Optional[datetime] = None
    class Config: from_attributes = True


# ═══════════════ 测试请求 ═══════════════

class TestRequestCreate(BaseModel):
    title: str
    project_code: Optional[str] = None
    product_code: Optional[str] = None
    test_type: str
    test_standard: Optional[str] = None
    trigger_mode: Optional[str] = None
    requester: str
    requirement: Optional[str] = None
    sample_info: Optional[str] = None
    priority: Optional[str] = None
    target_date: Optional[date] = None
    # Phase 6 增强字段
    vr_id: Optional[int] = None
    prototype_id: Optional[int] = None
    test_category: Optional[str] = None


class TestRequestOut(TestRequestCreate):
    id: int
    request_no: str
    status: str
    ng_count: int
    result_summary: Optional[str] = None
    results: list[TestResultOut] = []
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ MQ验证 ═══════════════

class MQVerificationCreate(BaseModel):
    part_no: str
    part_name: Optional[str] = None
    project_code: Optional[str] = None
    product_code: Optional[str] = None
    mq_type: str = "full"
    test_items: Optional[str] = None


class MQVerificationOut(MQVerificationCreate):
    id: int
    status: str
    pass_items: int = 0
    fail_items: int = 0
    verified_by: Optional[str] = None
    verified_at: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True
