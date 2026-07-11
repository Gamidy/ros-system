"""平台/系列/型号 Pydantic 模型"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PlatformCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=30)
    description: Optional[str] = None


class PlatformRead(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SeriesCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=30)
    platform_id: int


class SeriesRead(BaseModel):
    id: int
    name: str
    code: str
    platform_id: int
    platform: Optional[PlatformRead] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ModelCreate(BaseModel):
    model_number: str = Field(min_length=1, max_length=50)
    name: Optional[str] = None
    series_id: int
    rated_capacity: Optional[float] = None
    refrigerant: Optional[str] = None


class ModelRead(BaseModel):
    id: int
    model_number: str
    name: Optional[str]
    series_id: int
    series: Optional[SeriesRead] = None
    rated_capacity: Optional[float]
    refrigerant: Optional[str]
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
