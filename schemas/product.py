"""产品管理 — Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# ═══════════════ 产品平台 ═══════════════

class PlatformCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    platform_type: str = Field(pattern="^(IDU|ODU)$")
    status: str = "active"
    description: Optional[str] = None
    dimensions: Optional[str] = None
    hard_constraints: Optional[str] = None


class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    hard_constraints: Optional[str] = None


class PlatformOut(PlatformCreate):
    id: int
    created_at: datetime
    products_count: int = 0

    class Config:
        from_attributes = True


# ═══════════════ 产品型号 ═══════════════

class ProductCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    platform_id: int
    market: Optional[str] = None
    capacity: Optional[str] = None
    indoor_platform_id: Optional[int] = None
    outdoor_platform_id: Optional[int] = None
    indoor_product_code: Optional[str] = None
    outdoor_product_code: Optional[str] = None
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[str] = None


class ProductOut(ProductCreate):
    id: int
    status: str
    platform_code: str = ""
    market_codes: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════ 产品版本 ═══════════════

class VersionCreate(BaseModel):
    version_no: str = Field(min_length=1, max_length=50)
    reason: Optional[str] = None
    change_type: Optional[str] = None
    customer_perceivable: str = "false"
    effective_date: Optional[date] = None


class VersionStatusUpdate(BaseModel):
    status: str


class VersionOut(VersionCreate):
    id: int
    product_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ManufacturingVariantCreate(BaseModel):
    factory_code: str
    factory_name: Optional[str] = None
    mbom_version: str
    description: Optional[str] = None


class ManufacturingVariantOut(ManufacturingVariantCreate):
    id: int
    version_id: int
    is_active: str = "true"
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════ 目标市场与版本规则 ═══════════════

class MarketCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str
    region: Optional[str] = None
    energy_standard: Optional[str] = None
    energy_label: Optional[str] = None
    energy_unit: Optional[str] = None
    energy_standard_detail: Optional[str] = Field(None, max_length=100)
    national_standard: Optional[str] = Field(None, max_length=100)
    voltage_freq: Optional[str] = Field(None, max_length=50)
    cooling_max_temp: Optional[float] = None
    heating_min_temp: Optional[float] = None
    structure_type: Optional[str] = Field(None, max_length=100)
    main_selling_model: Optional[str] = Field(None, max_length=200)
    refrigerant: Optional[str] = Field(None, max_length=50)
    refrigerant_charge: Optional[float] = None
    is_active: str = "true"


class MarketOut(MarketCreate):
    code: str
    name: str

    class Config:
        from_attributes = True


class ProductMarketAssign(BaseModel):
    market_codes: list[str]


class VersionRuleRequest(BaseModel):
    change_description: str = ""
    material_level: str = "minor"
    change_category: str = "bom_only"
    is_customer_perceivable: bool = False


class VersionRuleResponse(BaseModel):
    should_create: bool
    reason: str = ""
    change_type: Optional[str] = None
    customer_perceivable: bool = False
    product_action: Optional[str] = None
