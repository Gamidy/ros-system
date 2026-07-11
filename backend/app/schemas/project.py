"""项目/WBS/任务 Schema"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=30)
    model_id: Optional[int] = None
    description: Optional[str] = None


class ProjectRead(BaseModel):
    id: int
    name: str
    code: str
    model_id: Optional[int] = None
    current_phase: str
    status: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WBSCreate(BaseModel):
    project_id: int
    parent_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=200)
    node_type: str = "work_package"
    sequence: int = 0


class WBSRead(BaseModel):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    name: str
    node_type: str
    sequence: int
    status: str
    children: List["WBSRead"] = []

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    wbs_id: int
    title: str = Field(min_length=1, max_length=300)
    assignee_id: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None


class TaskRead(BaseModel):
    id: int
    wbs_id: int
    assignee_id: Optional[int] = None
    title: str
    status: str
    priority: str
    due_date: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GateDecisionInput(BaseModel):
    decision: str = Field(pattern="^(go|kill|redirect|hold)$")
    comment: Optional[str] = None


class GateRead(BaseModel):
    id: int
    project_id: int
    phase: str
    decision: str
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
