"""BOM + Feature 相关 Schema"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Material ──
class MaterialCreate(BaseModel):
    material_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=30)
    specification: Optional[str] = None
    unit: str = "pcs"


class MaterialRead(BaseModel):
    id: int
    material_code: str
    name: str
    category: str
    specification: Optional[str] = None
    unit: str
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── BOM ──
class BOMNodeCreate(BaseModel):
    model_id: int
    material_id: int
    parent_id: Optional[int] = None
    quantity: float = 1.0
    node_type: str = "assembly"
    sequence: int = 0
    expression: Optional[str] = None


class BOMNodeRead(BaseModel):
    id: int
    model_id: int
    material_id: int
    parent_id: Optional[int] = None
    quantity: float
    node_type: str
    sequence: int
    children: List["BOMNodeRead"] = []
    material: Optional[MaterialRead] = None

    model_config = {"from_attributes": True}


# ── Feature ──
class FeatureOptionCreate(BaseModel):
    value: str = Field(min_length=1, max_length=100)
    code: Optional[str] = None
    sequence: int = 0


class FeatureOptionRead(BaseModel):
    id: int
    value: str
    code: Optional[str] = None
    sequence: int

    model_config = {"from_attributes": True}


class FeatureFamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=30)
    data_type: str = "enum"
    is_required: bool = True


class FeatureFamilyRead(BaseModel):
    id: int
    name: str
    code: str
    data_type: str
    is_required: bool
    options: List[FeatureOptionRead] = []

    model_config = {"from_attributes": True}
