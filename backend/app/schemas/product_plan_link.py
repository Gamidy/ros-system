"""产品策划-项目关联 — Pydantic Schema"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ProductPlanLinkCreate(BaseModel):
    """创建策划-项目关联"""
    project_id: int
    link_type: str = "primary"
    snapshot_data: Optional[str] = None


class ProductPlanLinkUpdate(BaseModel):
    """更新策划-项目关联（仅更新类型/快照）"""
    link_type: str
    snapshot_data: Optional[str] = None


class ProductPlanLinkOut(BaseModel):
    """策划-项目关联输出"""
    id: int
    product_plan_id: str
    project_id: int
    link_type: str
    snapshot_data: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductPlanLinkListOut(BaseModel):
    """策划-项目关联列表"""
    items: list[ProductPlanLinkOut]
    total: int
