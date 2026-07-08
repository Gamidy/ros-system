"""外协送样管理 — Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ═══════════════ 外协送样请求 ═══════════════

class OutsourceRequestCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=50)
    part_name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1)
    target_factory: str = Field(min_length=1, max_length=100)
    required_date: Optional[date] = None
    description: Optional[str] = None


class OutsourceRequestUpdate(BaseModel):
    status: Optional[str] = None
    required_date: Optional[date] = None
    description: Optional[str] = None


class OutsourceRequestOut(OutsourceRequestCreate):
    id: int
    request_no: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
