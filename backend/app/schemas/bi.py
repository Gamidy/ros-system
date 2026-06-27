"""BI分析看板 — 图表聚合查询 Schema"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class TrendItem(BaseModel):
    """立项趋势数据点"""
    month: str = Field(..., description="月份 YYYY-MM")
    count: int = Field(..., ge=0, description="立项数量")


class FunnelItem(BaseModel):
    """转化漏斗阶段数据点"""
    name: str = Field(..., description="阶段名称")
    value: int = Field(..., ge=0, description="策划数量")


class DistributionItem(BaseModel):
    """市场分布数据点"""
    name: str = Field(..., description="市场名称")
    value: int = Field(..., ge=0, description="策划数量")


class TrendResponse(BaseModel):
    """立项趋势响应"""
    items: list[TrendItem] = Field(default_factory=list)


class FunnelResponse(BaseModel):
    """转化漏斗响应"""
    items: list[FunnelItem] = Field(default_factory=list)


class DistributionResponse(BaseModel):
    """市场分布响应"""
    items: list[DistributionItem] = Field(default_factory=list)
