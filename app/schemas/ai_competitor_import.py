"""竞品AI导入 — Pydantic Schemas

TypeScript-compatible 数据结构，定义 AI 提取流程中各阶段的请求/响应模型。
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class ImportSourceType(str, Enum):
    """导入源类型"""
    URL = "url"
    TEXT = "text"
    FILE = "file"


class AIExtractedField(BaseModel):
    """单个提取字段（含置信度 + 原文证据）"""
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_quote: Optional[str] = None


class CompetitorExtraction(BaseModel):
    """单条竞品 AI 提取结果"""
    brand: AIExtractedField
    model: AIExtractedField
    product_type: AIExtractedField
    capacity_btu: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    capacity_kw: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    heating_capacity_btu: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    eer: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    seer: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    cop: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    indoor_noise_db: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    outdoor_noise_db: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    power_input_w: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    refrigerant: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    price: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    energy_label: AIExtractedField = Field(default_factory=lambda: AIExtractedField())
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_notes: Optional[str] = None


class AICompetitorImportResponse(BaseModel):
    """AI 导入预览阶段的响应"""
    session_id: str
    source_type: ImportSourceType
    target_market_id: int
    total_extracted: int
    extractions: list[CompetitorExtraction]


class CompetitorConfirmItem(BaseModel):
    """单条确认项：用户决定导入或跳过某条提取结果"""
    extraction_index: int
    action: Literal["import", "skip"]
    overrides: list[dict] = []


class AICompetitorConfirmRequest(BaseModel):
    """确认导入请求"""
    session_id: str
    target_market_id: Optional[int] = Field(default=None, description="（已弃用，从session读取）")
    confirmations: list[CompetitorConfirmItem]


class AICompetitorConfirmResponse(BaseModel):
    """确认导入响应"""
    session_id: str
    total_confirmed: int
    total_imported: int
    total_skipped: int
    imported_ids: list[int] = []
    failures: list[dict] = []


class AIImportSessionSummary(BaseModel):
    """导入历史中的单条记录摘要"""
    session_id: str
    source_type: ImportSourceType
    target_market_id: int
    created_at: datetime
    total_extracted: int
    total_imported: int
    total_skipped: int
    status: Literal["parsing", "preview", "completed", "failed"]


class AIImportHistoryResponse(BaseModel):
    """导入历史列表响应"""
    sessions: list[AIImportSessionSummary]
    total: int
