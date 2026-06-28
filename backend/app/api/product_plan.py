"""ProductPlan API — 聚合入口

从 4 个子模块重新导出所有路由和类型，保持向后兼容。
拆分后文件大小：1124 → 各子文件 ≤ 350 行 ✅

子模块:
  - product_plan_schemas — Pydantic Schemas + 辅助函数
  - product_plan_crud — 核心 CRUD 端点
  - product_plan_workflow_api — 流程推进 + 审批端点
  - product_plan_versions — 版本管理 + 批量操作端点
"""
import logging

from fastapi import APIRouter
from app.api.product_plan_schemas import (
    CostCreate, CostOut, PlanCreate, PlanUpdate, PlanOut, PlanStatusOut,
    NextActionOut, PlanDetailOut, PaginatedResult,
    _plan_to_dict, _cost_to_dict, _STAGE_ORDER,
)
from app.api.product_plan_crud import router as crud_router
from app.api.product_plan_workflow_api import router as workflow_router
from app.api.product_plan_versions import router as versions_router
from app.api.product_plan_review import router as review_router

logger = logging.getLogger(__name__)

# 聚合路由 — 所有子路由使用相同的 prefix，由 main.py 统一注册
# 注意: 路由由 main.py 直接 include 子模块，避免 extend 导致 FastAPI 不识别 prefix
router = APIRouter(prefix="/product-plans", tags=["产品策划"])

# 保留 review_router 的 extend（它在 main.py 单独 include 且没有 prefix 冲突问题）
router.routes.extend(review_router.routes)

__all__ = [
    "router", "review_router",
    "CostCreate", "CostOut", "PlanCreate", "PlanUpdate",
    "PlanOut", "PlanStatusOut", "NextActionOut", "PlanDetailOut", "PaginatedResult",
    "_plan_to_dict", "_cost_to_dict",
]
