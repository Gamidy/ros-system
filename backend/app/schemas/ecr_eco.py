"""Phase 2 — ECR/ECO Pydantic Schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── ECR Schemas ──────────────────────────────────────────

class ECRCreate(BaseModel):
    """创建 ECR"""
    title: str = Field(..., min_length=1, max_length=200)
    ecr_type: str = Field(default="other")
    reason: str = Field(..., min_length=1)
    urgency: str = Field(default="medium")
    affected_products: Optional[List[dict]] = None
    affected_documents: Optional[List[dict]] = None
    description: Optional[str] = None


class ECRUpdate(BaseModel):
    """更新 ECR（仅允许 draft 状态编辑）"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    ecr_type: Optional[str] = None
    reason: Optional[str] = None
    urgency: Optional[str] = None
    affected_products: Optional[List[dict]] = None
    affected_documents: Optional[List[dict]] = None
    description: Optional[str] = None


class ECRRejectRequest(BaseModel):
    """驳回 ECR"""
    rejection_reason: str = Field(..., min_length=1, max_length=500)


class ECRReviewRequest(BaseModel):
    """审批 ECR（通过/驳回）"""
    action: str = Field(..., pattern="^(approve|reject)$")
    rejection_reason: Optional[str] = Field(None, max_length=500)


class ECRSummaryOut(BaseModel):
    """ECR 摘要（列表用）"""
    id: int
    code: str
    title: str
    ecr_type: str
    urgency: str
    status: str
    submitter_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ECRAttachmentOut(BaseModel):
    """ECR 附件"""
    id: int
    ecr_id: int
    file_name: str
    file_type: Optional[str] = None
    file_size: int
    uploaded_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ECRDetailOut(BaseModel):
    """ECR 详情"""
    id: int
    code: str
    title: str
    ecr_type: str
    reason: str
    urgency: str
    affected_products: Optional[dict] = None
    affected_documents: Optional[dict] = None
    description: Optional[str] = None
    status: str
    submitter_id: int
    submitter_name: Optional[str] = None
    reviewer_id: Optional[int] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    attachments: List[ECRAttachmentOut] = []

    model_config = {"from_attributes": True}


# ── ECO Schemas ──────────────────────────────────────────

class ECOItemCreate(BaseModel):
    """ECO 明细项"""
    seq: int = 0
    change_type: str
    object_type: str
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class ECOItemUpdate(BaseModel):
    """更新 ECO 明细项"""
    seq: Optional[int] = None
    change_type: Optional[str] = None
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class ECOItemOut(BaseModel):
    """ECO 明细项输出"""
    id: int
    eco_id: int
    seq: int
    change_type: str
    object_type: str
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ECOCreate(BaseModel):
    """创建 ECO"""
    ecr_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    change_summary: str = Field(..., min_length=1)
    implementation_plan: Optional[str] = None
    effective_date: Optional[str] = None
    items: Optional[List[ECOItemCreate]] = None


class ECOUpdate(BaseModel):
    """更新 ECO（仅允许 draft 状态）"""
    title: Optional[str] = None
    change_summary: Optional[str] = None
    implementation_plan: Optional[str] = None
    effective_date: Optional[str] = None


class ECOOut(BaseModel):
    """ECO 摘要"""
    id: int
    code: str
    ecr_id: Optional[int] = None
    title: str
    status: str
    effective_date: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ECODetailOut(BaseModel):
    """ECO 详情"""
    id: int
    code: str
    ecr_id: Optional[int] = None
    title: str
    change_summary: str
    implementation_plan: Optional[str] = None
    effective_date: Optional[str] = None
    status: str
    created_by: int
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[ECOItemOut] = []

    model_config = {"from_attributes": True}
