"""产品策划↔项目多对多关联 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProductPlanProjectLinkOut(BaseModel):
    """关联输出"""
    id: int
    product_plan_id: str
    project_id: int
    link_type: str
    snapshot_data: Optional[str] = None
    version_major: int = 1
    version_minor: int = 0
    snapshot_schema_version: int = 1
    scenario_group_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductPlanProjectLinkCreate(BaseModel):
    """创建关联"""
    project_id: int
    link_type: str = "primary"
    snapshot_data: Optional[str] = None
    scenario_group_id: Optional[str] = None


class ProductPlanProjectLinkUpdate(BaseModel):
    """更新关联"""
    link_type: Optional[str] = None
    snapshot_data: Optional[str] = None
    version_major: Optional[int] = None
    version_minor: Optional[int] = None
    scenario_group_id: Optional[str] = None


# ── 向后兼容别名 ──
ProductPlanLinkOut = ProductPlanProjectLinkOut
ProductPlanLinkCreate = ProductPlanProjectLinkCreate
ProductPlanLinkUpdate = ProductPlanProjectLinkUpdate
