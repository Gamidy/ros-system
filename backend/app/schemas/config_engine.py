"""P0 — 配置引擎 Schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ConfigGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    series_id: int
    family_ids: Optional[str] = None


class ConfigGroupOut(BaseModel):
    id: int
    name: str
    series_id: int
    family_ids: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigRuleCreate(BaseModel):
    group_id: int
    rule_type: str = Field(..., pattern="^(requires|excludes)$")
    source_option_id: int
    target_option_id: int
    description: Optional[str] = None


class ConfigRuleOut(BaseModel):
    id: int
    group_id: int
    rule_type: str
    source_option_id: int
    target_option_id: int
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigValidateRequest(BaseModel):
    selected_option_ids: List[int]


class ConfigValidateResponse(BaseModel):
    valid: bool
    violations: List[str] = []
