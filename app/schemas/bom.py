"""BOM与物料管理 — Pydantic Schema"""

from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field


# ═══════════════ 物料主数据 ═══════════════


class PartCreate(BaseModel):
    part_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: str = "个"
    lifecycle: str = "developing"
    supplier_info: Optional[str] = None
    risk_level: str = "low"
    is_cdf_item: bool = False
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: bool = False
    mrc_level: Optional[str] = None


class PartOut(BaseModel):
    id: int
    part_no: str
    name: str
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: str
    lifecycle: str
    risk_level: str
    supplier_info: Optional[str] = None
    is_cdf_item: bool = False
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: bool = False
    mq_status: Optional[str] = None
    mrc_level: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class PartUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    lifecycle: Optional[str] = None
    risk_level: Optional[str] = None
    is_cdf_item: Optional[bool] = None
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: Optional[bool] = None
    mrc_level: Optional[str] = None


class PartDetailOut(BaseModel):
    id: int
    part_no: str
    name: str
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: str
    lifecycle: str
    risk_level: str
    supplier_info: Optional[str] = None
    is_cdf_item: bool = False
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: bool = False
    mq_status: Optional[str] = None
    mrc_level: Optional[str] = None
    avl_entries: list["PartAVLOut"] = []
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 供应商物料 AVL ═══════════════


class PartAVLCreate(BaseModel):
    vendor_code: str = Field(min_length=1, max_length=50)
    vendor_name: str = Field(min_length=1, max_length=200)
    is_primary: bool = False
    status: str = "approved"
    approved_date: Optional[date] = None
    remark: Optional[str] = None


class PartAVLOut(PartAVLCreate):
    id: int
    part_id: int
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ BOM 定义 ═══════════════


class BOMCreate(BaseModel):
    bom_no: str = Field(min_length=1, max_length=50)
    product_code: str = Field(min_length=1, max_length=50)
    version: str = "V1.0"
    bom_type: str = "MBOM"
    description: Optional[str] = None
    factory_code: Optional[str] = None


class BOMUpdate(BaseModel):
    version: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class BOMOut(BaseModel):
    id: int
    bom_no: str
    product_code: str
    version: str
    bom_type: str
    description: Optional[str] = None
    factory_code: Optional[str] = None
    status: str
    created_at: datetime
    class Config: from_attributes = True


class BOMItemCreate(BaseModel):
    parent_item_id: Optional[int] = None
    part_no: str
    part_name: Optional[str] = None
    item_type: str = "Part"
    level: int = Field(ge=1, le=6)
    quantity: float = 1.0
    unit: str = "个"
    unit_price: float = 0.0
    amount: float = 1.0
    position_no: Optional[str] = None
    remark: Optional[str] = None


class BOMItemOut(BOMItemCreate):
    id: int
    bom_id: int
    children: Optional[list["BOMItemOut"]] = None
    created_at: datetime
    class Config: from_attributes = True


class AlternativeAssign(BaseModel):
    alternative_part_ids: list[int]


class BOMTreeItem(BaseModel):
    id: int
    part_no: str
    part_name: Optional[str] = None
    item_type: str
    level: int
    quantity: float
    unit: str = "个"
    unit_price: float = 0.0
    amount: float = 1.0
    position_no: Optional[str] = None
    remark: Optional[str] = None
    children: list["BOMTreeItem"] = []


class BOMTreeOut(BaseModel):
    bom: BOMOut
    tree: list[BOMTreeItem]


# ═══════════════ BOM 成本汇总 ═══════════════


class BOMCostByLevel(BaseModel):
    """各级成本统计"""
    level: int
    level_name: str  # 如 "L1-整机", "L2-内外机"
    item_count: int
    total_cost: float


class BOMCostNode(BaseModel):
    """BOM树节点含成本 — 递归结构"""
    id: int
    part_no: str
    part_name: Optional[str] = None
    item_type: str
    level: int
    quantity: float
    unit: str = "个"
    unit_price: float = 0.0
    amount: float = 1.0
    node_cost: float = 0.0  # 本节点直接成本 = unit_price × amount × quantity
    subtree_cost: float = 0.0  # 子树总成本（含本节点+所有子节点）
    children: list["BOMCostNode"] = []


class BOMCostSummaryOut(BaseModel):
    """BOM成本汇总响应"""
    bom: BOMOut
    total_cost: float = 0.0
    cost_by_level: list[BOMCostByLevel] = []
    tree_with_cost: list[BOMCostNode] = []
