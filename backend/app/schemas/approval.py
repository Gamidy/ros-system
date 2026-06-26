"""审批工作流 — Pydantic Schema"""
import json

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Any
from datetime import datetime


# ═══════════════ 审批步骤与链 ═══════════════

class ApprovalStepCreate(BaseModel):
    seq: int
    role: str
    name: str
    step_type: str = "sequential"


class ApprovalStepOut(ApprovalStepCreate):
    id: int
    chain_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApprovalChainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None
    steps: list[ApprovalStepCreate] = []


class ApprovalChainOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    steps: list[ApprovalStepOut] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ 审批请求与记录 ═══════════════

class ApprovalRequestCreate(BaseModel):
    chain_id: int
    request_type: str = Field(pattern="^(ecr|purchase|register|proposal)$")
    request_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=200)
    requester: Optional[str] = None


class ApprovalRequestOut(BaseModel):
    id: int
    chain_id: int
    request_type: str
    request_id: Optional[int] = None
    title: str
    requester: str
    status: str
    current_step: int
    step_meta: Optional[Any] = None
    steps: list[ApprovalStepOut] = []
    records: list["ApprovalRecordOut"] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("step_meta", mode="before")
    @classmethod
    def parse_step_meta(cls, v: Any) -> Any:
        """Parse step_meta from JSON string to dict if needed (SQLite stores JSON as TEXT)"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class ApprovalRecordOut(BaseModel):
    id: int
    request_id: int
    step_id: Optional[int] = None
    approver: str
    decision: str
    comment: Optional[str] = None
    decided_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApprovalDecision(BaseModel):
    comment: Optional[str] = None
