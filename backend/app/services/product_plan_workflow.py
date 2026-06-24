"""ProductPlan 流程引擎

职责：
- 创建产品策划（DRAFT）
- 推进流程（stage→stage），校验前置条件
- 获取下一步动作（UX核心）
- APPROVED → 自动生成 Project
"""
from datetime import datetime
import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.models.product_plan import ProductPlan, ProductPlanStage, Cost, CostType
from app.models.project import Project
from app.services.events import bus, EventTypes


# ── 阶段转换规则 ──
PLAN_STAGE_TRANSITIONS: dict[ProductPlanStage, list[ProductPlanStage]] = {
    ProductPlanStage.DRAFT: [ProductPlanStage.COMPETITOR],
    ProductPlanStage.COMPETITOR: [ProductPlanStage.DEFINITION],
    ProductPlanStage.DEFINITION: [ProductPlanStage.COSTING],
    ProductPlanStage.COSTING: [ProductPlanStage.TECH_INPUT],
    ProductPlanStage.TECH_INPUT: [ProductPlanStage.PROJECT_INIT],
    ProductPlanStage.PROJECT_INIT: [ProductPlanStage.APPROVED],
    ProductPlanStage.APPROVED: [ProductPlanStage.RELEASED],
    ProductPlanStage.RELEASED: [],
}

# ── 各阶段推进条件 ──
STAGE_REQUIREMENTS: dict[ProductPlanStage, list[dict]] = {
    ProductPlanStage.COMPETITOR: [
        {"field": "name", "label": "策划名称", "check": lambda p: bool(p.name)},
    ],
    ProductPlanStage.DEFINITION: [
        {"field": "competitor_id", "label": "竞品分析", "check": lambda p: p.competitor_id is not None},
        {"field": "series", "label": "产品系列", "check": lambda p: bool(p.series)},
        {"field": "market", "label": "目标市场", "check": lambda p: bool(p.market)},
    ],
    ProductPlanStage.COSTING: [
        {"field": "cost_target", "label": "成本目标", "check": lambda p: bool(p.cost_target)},
    ],
    ProductPlanStage.TECH_INPUT: [
        {"field": "performance_target", "label": "技术指标", "check": lambda p: bool(p.performance_target)},
    ],
    ProductPlanStage.PROJECT_INIT: [
        {"field": "costs", "label": "成本明细", "check": lambda p: p.costs and len(p.costs) > 0},
    ],
    ProductPlanStage.APPROVED: [
        {"field": "name", "label": "策划名称", "check": lambda p: bool(p.name)},
    ],
    ProductPlanStage.RELEASED: [],  # 发布无需条件
}

# ── 阶段中文名映射（给前端用） ──
STAGE_LABELS: dict[ProductPlanStage, str] = {
    ProductPlanStage.DRAFT: "草稿",
    ProductPlanStage.COMPETITOR: "竞品分析",
    ProductPlanStage.DEFINITION: "产品定义",
    ProductPlanStage.COSTING: "成本目标",
    ProductPlanStage.TECH_INPUT: "技术方案",
    ProductPlanStage.PROJECT_INIT: "立项审批",
    ProductPlanStage.APPROVED: "已批准",
    ProductPlanStage.RELEASED: "已发布",
}

# ── 阶段→业务事件映射 ──
STAGE_TO_EVENT: dict[ProductPlanStage, str] = {
    ProductPlanStage.COMPETITOR: EventTypes.PLAN_COMPETITOR_DONE,
    ProductPlanStage.DEFINITION: EventTypes.PLAN_DEFINITION_DONE,
    ProductPlanStage.COSTING: EventTypes.PLAN_COSTING_DONE,
    ProductPlanStage.TECH_INPUT: EventTypes.PLAN_TECH_INPUT_DONE,
    ProductPlanStage.PROJECT_INIT: EventTypes.PLAN_PROJECT_INIT_DONE,
    ProductPlanStage.APPROVED: EventTypes.PLAN_APPROVED,
    ProductPlanStage.RELEASED: EventTypes.PLAN_RELEASED,
}


def create_product_plan(db: Session, data: dict, username: str) -> ProductPlan:
    """创建 DRAFT 状态产品策划"""
    plan = ProductPlan(
        name=data.get("name", ""),
        series=data.get("series"),
        market=data.get("market"),
        competitor_id=data.get("competitor_id"),
        cost_target=data.get("cost_target"),
        performance_target=data.get("performance_target"),
        status=ProductPlanStage.DRAFT,
        created_by=username,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def advance_stage(db: Session, plan_id: str, username: str) -> ProductPlan:
    """推进 ProductPlan 到一个新的 stage

    流程：
    1. 查找 plan
    2. 校验当前 stage → 目标 stage 是否合法
    3. 检查 STAGE_REQUIREMENTS 条件
    4. 更新 status
    5. 若 APPROVED → 自动创建 Project
    6. commit
    """
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    current = plan.status
    allowed_next = PLAN_STAGE_TRANSITIONS.get(current, [])
    if not allowed_next:
        raise HTTPException(status_code=400, detail=f"当前阶段「{STAGE_LABELS.get(current, current.value)}」已无下一步")

    # 取第一个合法目标阶段
    target = allowed_next[0]

    # 校验条件
    requirements = STAGE_REQUIREMENTS.get(target, [])
    failures = [req for req in requirements if not req["check"](plan)]
    if failures:
        missing = [f["label"] for f in failures]
        raise HTTPException(
            status_code=400,
            detail=f"推进到「{STAGE_LABELS.get(target, target.value)}」前需要先完成: {'、'.join(missing)}",
        )

    # 更新状态
    plan.status = target

    # APPROVED → 自动创建 Project
    if target == ProductPlanStage.APPROVED:
        project = _generate_project_from_plan(plan, db, username)
        plan.project_id = project.id

    db.commit()
    db.refresh(plan)

    # ── 事件发射 ──
    try:
        event_type = STAGE_TO_EVENT.get(target)
        if event_type:
            event_kwargs = {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "username": username,
                "new_stage": STAGE_LABELS.get(target, target.value),
            }
            if target == ProductPlanStage.APPROVED:
                event_kwargs["project_id"] = plan.project_id
                event_kwargs["created_by"] = plan.created_by
            # 发射业务事件 (异步，不阻塞主流程)
            bus.emit_async(event_type, **event_kwargs)
            # 发射副作用事件 (审计+通知)
            bus.emit_async(EventTypes.PLAN_AUDIT_LOG, **event_kwargs)
            bus.emit_async(EventTypes.PLAN_NOTIFY_PM, **event_kwargs)
    except Exception as e:
        logger.error("advance_stage 事件发射失败: %s", e, exc_info=True)

    return plan


def get_next_action(db: Session, plan_id: str) -> dict:
    """获取下一步动作引导（UX核心）"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")

    current = plan.status
    allowed_next = PLAN_STAGE_TRANSITIONS.get(current, [])
    current_label = STAGE_LABELS.get(current, current.value)

    # 当前阶段的检查清单
    current_requirements = STAGE_REQUIREMENTS.get(current, [])
    missing_current = [req["label"] for req in current_requirements if not req["check"](plan)]

    if not allowed_next:
        # 已到最后阶段
        return {
            "current_stage": current_label,
            "next_stage": None,
            "next_action": "流程已完成",
            "missing_fields": [],
            "can_advance": False,
        }

    target = allowed_next[0]
    target_label = STAGE_LABELS.get(target, target.value)
    target_requirements = STAGE_REQUIREMENTS.get(target, [])

    # 推进到下一阶段还缺什么
    missing_for_next = [req["label"] for req in target_requirements if not req["check"](plan)]

    # 如果当前阶段自己还有未完成项，优先提示
    if missing_current:
        next_action = f"完成当前阶段「{current_label}」: {'、'.join(missing_current)}"
    elif missing_for_next:
        next_action = f"准备下一阶段「{target_label}」: {'、'.join(missing_for_next)}"
    else:
        next_action = f"推进到下一阶段「{target_label}」"

    return {
        "current_stage": current_label,
        "next_stage": target_label,
        "next_action": next_action,
        "missing_fields": missing_for_next if not missing_current else missing_current,
        "can_advance": len(missing_current) == 0 and len(missing_for_next) == 0,
    }


def _generate_project_from_plan(plan: ProductPlan, db: Session, username: str) -> Project:
    """APPROVED 时自动生成 Project（将策划数据映射到项目字段）"""
    from datetime import date

    # 解析 cost_target JSON
    cost_target_data = {}
    if plan.cost_target:
        try:
            cost_target_data = json.loads(plan.cost_target)
        except (json.JSONDecodeError, TypeError):
            pass

    # 生成项目名
    project_name = f"策划项目-{plan.name}" if plan.name else "产品策划项目"

    # 生成编码
    today = date.today()
    code_suffix = today.strftime("%y%m%d") + f"{plan.id[:4].upper()}" if plan.id else today.strftime("%y%m%d")
    code = f"P-{code_suffix}"

    # 从 costs 表提取成本目标
    target_cost = 0
    if plan.costs:
        for c in plan.costs:
            if c.cost_type == CostType.TARGET and c.target_value:
                target_cost += c.target_value

    project = Project(
        code=code,
        name=project_name,
        project_class="C级",
        source="产品策划",
        source_category="product_creation",
        status="planning",
        owner=username,
        budget=int(target_cost) if target_cost > 0 else None,
        market_policy=plan.market,
        annual_planning_ref=plan.name,
        product_type=plan.series,
    )
    db.add(project)
    db.flush()  # 获取 project.id
    return project
