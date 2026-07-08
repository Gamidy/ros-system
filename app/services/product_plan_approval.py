"""ProductPlan 审批集成服务

职责：
- 创建产品策划审批请求 (ApprovalRequest)
- 审批完成后推进 ProductPlan → APPROVED 并生成 Project
- 驳回时回退 ProductPlan → DEFINITION
"""
import json
import logging
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest, ApprovalRecord
from app.services.events import bus, EventTypes

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# 审批链管理
# ════════════════════════════════════════════════════════


def _get_or_create_plan_approval_chain(db: Session) -> ApprovalChain:
    """查找或创建 PLAN_APPROVAL 审批链"""
    chain = db.query(ApprovalChain).filter(
        ApprovalChain.name == "PLAN_APPROVAL"
    ).first()
    if chain:
        return chain

    chain = ApprovalChain(
        name="PLAN_APPROVAL",
        code="PLAN_APPROVAL",
        description="产品策划审批链",
    )
    db.add(chain)
    db.flush()

    # Step 1: 并行审批（四角色）
    parallel_roles = [
        ("rd_director", "研发总监"),
        ("product_manager", "产品经理"),
        ("systems_engineer", "系统工程师"),
        ("quality_engineer", "品质工程师"),
    ]
    for role, name in parallel_roles:
        step = ApprovalStep(
            chain_id=chain.id,
            seq=1,
            role=role,
            name=name,
            step_type="parallel",
        )
        db.add(step)

    # Step 2: 研发总监终审（顺序）
    director_step = ApprovalStep(
        chain_id=chain.id,
        seq=2,
        role="director_review",
        name="研发总监终审",
        step_type="sequential",
    )
    db.add(director_step)
    db.flush()

    logger.info("PLAN_APPROVAL 审批链已创建: chain_id=%s", chain.id)
    return chain


# ════════════════════════════════════════════════════════
# 创建审批请求
# ════════════════════════════════════════════════════════


def create_plan_approval(plan_id: str, db: Session, current_user: str, comment: Optional[str] = None) -> ApprovalRequest:
    """为 ProductPlan 创建审批请求

    Args:
        plan_id: ProductPlan UUID
        db: 数据库 Session
        current_user: 当前操作用户名

    Returns:
        ApprovalRequest 实例

    Raises:
        HTTPException(404): 策划不存在
    """
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="策划不存在")

    # 获取或创建审批链
    chain = _get_or_create_plan_approval_chain(db)

    # 创建审批请求
    request = ApprovalRequest(
        chain_id=chain.id,
        request_type="product_plan",
        request_id=None,  # ProductPlan id 是 UUID String → 存入 step_meta
        title=f"产品策划审批: {plan.name}",
        requester=current_user,
        status="pending",
        current_step=1,
        step_meta={
            "plan_id": plan_id,
            "plan_name": plan.name,
            "created_by": plan.created_by,
            "comment": comment,
        },
    )
    db.add(request)
    db.flush()

    logger.info(
        "Plan approval created: plan=%s, request=%s, requester=%s",
        plan_id, request.id, current_user,
    )

    # ── 发射审批待处理通知 ──
    try:
        bus.emit_async(
            "approval.pending",
            plan_id=plan_id,
            plan_name=plan.name,
            requester=current_user,
            username=current_user,
        )
    except Exception as e:
        logger.exception("approval.pending 事件发射失败: %s", e)

    return request


# ════════════════════════════════════════════════════════
# 事件处理器
# ════════════════════════════════════════════════════════


def on_approval_completed(request_id: int, request_type: str, **kwargs):
    """审批完成事件处理器

    当 type="product_plan" 的审批完成时：
    1. 查找关联 ProductPlan
    2. 推进到 APPROVED 阶段
    3. 创建 Project（复用 _generate_project_from_plan）
    4. 发射 plan.approved 事件
    """
    if request_type != "product_plan":
        return

    db: Session = SessionLocal()
    try:
        request = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        if not request:
            logger.error("Approval request not found: id=%s", request_id)
            return

        # 从 step_meta 解析 plan_id
        plan_id = None
        if request.step_meta:
            try:
                meta = json.loads(request.step_meta) if isinstance(request.step_meta, str) else request.step_meta
                plan_id = meta.get("plan_id")
            except (json.JSONDecodeError, TypeError, AttributeError):
                logger.error("Failed to parse step_meta for request=%s", request_id)

        if not plan_id:
            logger.error("No plan_id in approval request step_meta: request_id=%s", request_id)
            return

        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            logger.error("ProductPlan not found: id=%s", plan_id)
            return

        # 推进到 APPROVED
        plan.status = ProductPlanStage.APPROVED

        from app.services.product_plan_workflow import _generate_project_from_plan
        from app.models.product_plan import ProductPlanProjectLink
        username = kwargs.get("username", request.requester)

        # 幂等性检查：避免重复创建 Project + Link
        existing_link = db.query(ProductPlanProjectLink).filter(
            ProductPlanProjectLink.product_plan_id == plan.id,
            ProductPlanProjectLink.link_type == 'primary'
        ).first()
        if existing_link:
            logger.warning(
                "Project already exists for plan=%s, project_id=%s, skipping creation",
                plan.id, existing_link.project_id,
            )
            project_id = existing_link.project_id
        else:
            project = _generate_project_from_plan(plan, db, username)
            link = ProductPlanProjectLink(
                product_plan_id=plan.id,
                project_id=project.id,
                link_type='primary',
            )
            db.add(link)
            project_id = project.id

        db.commit()
        db.refresh(plan)

        logger.info(
            "Plan approval completed: plan=%s, project=%s, request=%s",
            plan_id, project_id, request_id,
        )

        # 发射 plan.approved 事件（触发 Saga 后续步骤）
        bus.emit_async(
            EventTypes.PLAN_APPROVED,
            plan_id=plan.id,
            plan_name=plan.name,
            project_id=project_id,
            created_by=plan.created_by or request.requester,
            username=username,
        )

    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        logger.error("on_approval_completed 处理失败: %s", e, exc_info=True)
    finally:
        db.close()


def on_proposal_rejected(request_id: int, request_type: str, **kwargs):
    """审批驳回事件处理器

    当 type="product_plan" 的审批被驳回时：
    将 ProductPlan 回退到 DEFINITION 阶段
    """
    if request_type != "product_plan":
        return

    db: Session = SessionLocal()
    try:
        request = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        if not request:
            logger.error("Approval request not found: id=%s", request_id)
            return

        # 从 step_meta 解析 plan_id
        plan_id = None
        if request.step_meta:
            try:
                meta = json.loads(request.step_meta) if isinstance(request.step_meta, str) else request.step_meta
                plan_id = meta.get("plan_id")
            except (json.JSONDecodeError, TypeError, AttributeError):
                logger.error("Failed to parse step_meta for request=%s", request_id)

        if not plan_id:
            logger.error("No plan_id in approval request step_meta: request_id=%s", request_id)
            return

        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        if not plan:
            logger.error("ProductPlan not found: id=%s", plan_id)
            return

        # 回退到 DEFINITION
        plan.status = ProductPlanStage.DEFINITION
        db.commit()

        logger.info(
            "Plan proposal rejected: plan=%s reverted to DEFINITION, request=%s",
            plan_id, request_id,
        )

    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        logger.error("on_proposal_rejected 处理失败: %s", e, exc_info=True)
    finally:
        db.close()
