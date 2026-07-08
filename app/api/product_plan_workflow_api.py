"""ProductPlan Workflow API — 流程推进 + 审批端点

从 product_plan.py 提取的流程推进和审批相关 API 端点。
包含 6 个端点:
  - POST /{plan_id}/advance      — 推进流程
  - POST /{plan_id}/approve      — 审批通过
  - POST /{plan_id}/reject       — 驳回
  - POST /{plan_id}/withdraw     — 撤回
  - PATCH /{plan_id}/stage       — 直接设置阶段
  - GET  /{plan_id}/next-action   — 下一步引导
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.product_plan_schemas import (
    AdvancePlanRequest,
    SetStageRequest,
    NextActionOut,
    _plan_to_dict,
    _cost_to_dict,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.schemas.product_plan_link import ProductPlanLinkOut
from app.services.product_plan_workflow import (
    advance_stage as workflow_advance,
    get_next_action as workflow_next_action,
    STAGE_LABELS,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/product-plans", tags=["产品策划-流程审批"])


# ── advance ──


@router.post("/{plan_id}/advance")
def advance_plan_stage(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """推进策划流程（[P0-3] 支持审批意见参数）"""
    plan = workflow_advance(db, plan_id, current_user.username, comment=req.comment)
    result = _plan_to_dict(plan)
    result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
    result["project_links"] = [
        ProductPlanLinkOut.model_validate(l) for l in (plan.project_links or [])
    ]
    return result


# ── approve ──


@router.post("/{plan_id}/approve")
def approve_plan(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """通过产品策划审批。

    将策划推进至 APPROVED 阶段，同时创建审批请求记录。
    仅允许在 PROJECT_INIT 阶段的策划执行此操作。

    Args:
        plan_id: 策划 ID（路径参数）
        req: 审批请求体，包含 comment 审批意见

    Returns:
        dict: 更新后的策划详情，包含 costs 和 project_links

    Raises:
        HTTPException 404: 策划不存在
        HTTPException 400: 当前阶段不允许审批操作
        HTTPException 500: 审批操作失败（内部错误）
    """
    try:
        plan = workflow_advance(db, plan_id, current_user.username, comment=req.comment)
        result = _plan_to_dict(plan)
        result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
        result["project_links"] = [
            ProductPlanLinkOut.model_validate(l) for l in (plan.project_links or [])
        ]
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        raise HTTPException(status_code=500, detail=f"审批操作失败: {str(e)}")


# ── reject ──


@router.post("/{plan_id}/reject")
def reject_plan(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """驳回产品策划。

    将策划退回至 DEFINITION 阶段。
    仅允许在 PROJECT_INIT 阶段的策划执行此操作。

    Args:
        plan_id: 策划 ID（路径参数）
        req: 驳回请求体，包含 comment 驳回意见

    Returns:
        dict: 更新后的策划基本信息

    Raises:
        HTTPException 404: 策划不存在
        HTTPException 400: 当前阶段不可驳回（仅 PROJECT_INIT 允许）
        HTTPException 500: 驳回操作失败（内部错误）
    """
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        if plan.status != ProductPlanStage.PROJECT_INIT:
            raise HTTPException(
                status_code=400,
                detail=f"当前阶段「{STAGE_LABELS.get(plan.status, plan.status.value)}」不可驳回，仅 PROJECT_INIT 阶段允许驳回",
            )

        plan.status = ProductPlanStage.DEFINITION
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"驳回操作失败: {str(e)}")


# ── withdraw ──


@router.post("/{plan_id}/withdraw")
def withdraw_plan(
    plan_id: str,
    req: AdvancePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """撤回产品策划。

    将策划退回至 DRAFT 阶段。
    已批准（APPROVED）或已发布（RELEASED）的策划不可撤回。

    Args:
        plan_id: 策划 ID（路径参数）
        req: 撤回请求体，包含 comment 撤回说明

    Returns:
        dict: 更新后的策划基本信息

    Raises:
        HTTPException 404: 策划不存在
        HTTPException 400: 当前阶段不可撤回（APPROVED/RELEASED 阶段）
        HTTPException 500: 撤回操作失败（内部错误）
    """
    try:
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        if plan.status in (ProductPlanStage.APPROVED, ProductPlanStage.RELEASED):
            raise HTTPException(
                status_code=400,
                detail=f"当前阶段「{STAGE_LABELS.get(plan.status, plan.status.value)}」不可撤回",
            )

        plan.status = ProductPlanStage.DRAFT
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"撤回操作失败: {str(e)}")


# ── set stage ──


@router.patch("/{plan_id}/stage")
def set_plan_stage(
    plan_id: str,
    data: SetStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """直接设置策划阶段。

    将策划手动设置为指定的目标阶段。此操作直接修改数据库中的 status 字段。
    仅 admin 和 general_manager 角色可执行此操作。

    Args:
        plan_id: 策划 ID（路径参数）
        data: 设置请求体，包含 target stage 值

    Returns:
        dict: 更新后的策划详情，包含 costs 和 project_links

    Raises:
        HTTPException 403: 当前用户无权限（非 admin 或 general_manager）
        HTTPException 404: 策划不存在
        HTTPException 400: 无效的阶段值
        HTTPException 500: 设置阶段失败（内部错误）
    """
    try:
        if current_user.role not in ("admin", "general_manager"):
            raise HTTPException(status_code=403, detail="仅管理员和总经理可执行此操作")

        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="策划不存在")

        try:
            new_stage = ProductPlanStage(data.stage)
        except ValueError:
            valid = [s.value for s in ProductPlanStage]
            raise HTTPException(
                status_code=400,
                detail=f"无效阶段值: {data.stage}，有效值: {', '.join(valid)}",
            )

        plan.status = new_stage
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)

        result = _plan_to_dict(plan)
        result["costs"] = [_cost_to_dict(c) for c in (plan.costs or [])]
        result["project_links"] = [
            ProductPlanLinkOut.model_validate(l) for l in (plan.project_links or [])
        ]
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"设置阶段失败: {str(e)}")


# ── next-action ──


@router.get("/{plan_id}/next-action", response_model=NextActionOut)
def get_next_action(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> NextActionOut:
    """获取下一步动作引导"""
    return workflow_next_action(db, plan_id)
