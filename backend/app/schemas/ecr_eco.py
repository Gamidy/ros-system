"""Phase 6 S3 — ECR/ECO 工程变更控制 Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime


# ═══════════════ 区域1 — ECR附件 ═══════════════

class ECRAttachmentOut(BaseModel):
    """ECR附件输出"""
    id: int
    ecr_id: int
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: int = 0
    uploaded_by: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域2 — ECR（新版） ═══════════════

class ECRCreate(BaseModel):
    """创建ECR"""
    title: str = Field(min_length=1, max_length=200)
    ecr_type: str = "other"
    reason: str = Field(min_length=1)
    urgency: str = "medium"
    affected_products: Optional[str] = None
    affected_documents: Optional[str] = None
    description: Optional[str] = None


class ECRUpdate(BaseModel):
    """更新ECR"""
    title: Optional[str] = None
    ecr_type: Optional[str] = None
    reason: Optional[str] = None
    urgency: Optional[str] = None
    affected_products: Optional[str] = None
    affected_documents: Optional[str] = None
    description: Optional[str] = None


class ECROut(BaseModel):
    """ECR列表输出"""
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
    workflow_id: Optional[int] = None
    submitter_id: int
    submitter_name: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    attachment_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ECRDetailOut(ECROut):
    """ECR详情输出（含附件+关联ECO）"""
    attachments: list[ECRAttachmentOut] = []
    eco_code: Optional[str] = None
    eco_id: Optional[int] = None
    eco_status: Optional[str] = None


class ECRSummaryOut(BaseModel):
    """ECR简要信息（用于ECO关联展示）"""
    id: int
    code: str
    title: str
    ecr_type: str
    status: str
    submitter_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ECRRejectRequest(BaseModel):
    """驳回ECR"""
    rejection_reason: str = Field(min_length=1)


# ═══════════════ 区域3 — ECO明细项 ═══════════════

class ECOItemCreate(BaseModel):
    """创建ECO明细项"""
    change_type: str
    object_type: str
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class ECOItemUpdate(BaseModel):
    """更新ECO明细项"""
    change_type: Optional[str] = None
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class ECOItemOut(ECOItemCreate):
    """ECO明细项输出"""
    id: int
    eco_id: int
    seq: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 区域4 — ECO ═══════════════

class ECOCreate(BaseModel):
    """创建ECO"""
    ecr_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=200)
    change_summary: str = Field(min_length=1)
    implementation_plan: Optional[str] = None
    effective_date: Optional[date] = None
    items: list[ECOItemCreate] = []


class ECOUpdate(BaseModel):
    """更新ECO"""
    title: Optional[str] = None
    change_summary: Optional[str] = None
    implementation_plan: Optional[str] = None
    effective_date: Optional[date] = None


class ECOOut(BaseModel):
    """ECO列表输出"""
    id: int
    code: str
    ecr_id: Optional[int] = None
    title: str
    change_summary: str
    implementation_plan: Optional[str] = None
    effective_date: Optional[date] = None
    status: str
    created_by: int
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    closed_at: Optional[datetime] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ECODetailOut(ECOOut):
    """ECO详情输出（含明细项+关联ECR）"""
    items: list[ECOItemOut] = []
    ecr_code: Optional[str] = None
    ecr_title: Optional[str] = None


class ECOSummaryOut(BaseModel):
    """ECO简要信息（用于ECR关联展示）"""
    id: int
    code: str
    title: str
    status: str
    effective_date: Optional[date] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ECOChDashboardOut(BaseModel):
    """ECO变更看板"""
    status_summary: dict[str, int] = {}
    type_distribution: dict[str, int] = {}
    this_month_new: int = 0
    pending_verification: int = 0
    changes: list[ECOOut] = []
    model_config = ConfigDict(from_attributes=True)
