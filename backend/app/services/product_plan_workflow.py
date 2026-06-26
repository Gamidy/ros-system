"""ProductPlan 流程引擎

职责：
- 创建产品策划（DRAFT）
- 推进流程（stage→stage），校验前置条件
- 获取下一步动作（UX核心）
- APPROVED → 创建 ApprovalRequest（代替自动生成 Project）
"""
from datetime import datetime
import json
import logging
from typing import Tuple, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.models.product_plan import ProductPlan, ProductPlanStage, Cost, CostType
from app.models.project import Project
from app.services.events import bus, EventTypes
from app.models.workflow_transition_spec import WorkflowTransitionSpec


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


def _load_transitions(db: Session) -> list[WorkflowTransitionSpec]:
    """从 DB 加载流程转换规则；DB 为空时自动初始化种子数据"""
    specs = db.query(WorkflowTransitionSpec).order_by(WorkflowTransitionSpec.sort_order).all()
    if not specs:
        logger.info("WorkflowTransitionSpec 为空，写入默认转换规则...")
        _init_default_transitions(db)
        specs = db.query(WorkflowTransitionSpec).order_by(WorkflowTransitionSpec.sort_order).all()
    return specs


def _init_default_transitions(db: Session):
    """写入 WorkflowTransitionSpec 默认种子数据"""
    from app.models.workflow_transition_spec import WorkflowTransitionSpec as WTS
    defaults = [
        WTS(from_stage="draft", to_stage="competitor", sort_order=1),
        WTS(from_stage="competitor", to_stage="definition", sort_order=2, required_fields='["competitor_id","initiation","market_info"]'),
        WTS(from_stage="definition", to_stage="costing", sort_order=3, required_fields='["cost_target"]'),
        WTS(from_stage="costing", to_stage="tech_input", sort_order=4, required_fields='["performance_target","tech_spec"]'),
        WTS(from_stage="tech_input", to_stage="project_init", sort_order=5, required_fields='["initiation","market_info","tech_spec","team_members"]'),
        WTS(from_stage="project_init", to_stage="approved", sort_order=6, required_fields='["initiation","market_info","tech_spec","team_members","costs"]'),
        WTS(from_stage="approved", to_stage="released", sort_order=7),
    ]
    for spec in defaults:
        db.add(spec)
    db.commit()
    logger.info("WorkflowTransitionSpec 种子数据已写入 (%d 条)", len(defaults))


def _load_requirements_for_stage(db: Session, stage: ProductPlanStage) -> list[dict]:
    """从 DB 加载阶段前置条件；DB 为空时回退到 STAGE_REQUIREMENTS 常量

    返回 list[dict]，每个 dict 含 field / label / check 键
    """
    specs = db.query(WorkflowTransitionSpec).filter(
        WorkflowTransitionSpec.to_stage == stage.value
    ).all()
    if not specs:
        return STAGE_REQUIREMENTS.get(stage, [])

    requirements = []
    for spec in specs:
        if spec.required_fields:
            try:
                fields = json.loads(spec.required_fields)
            except (json.JSONDecodeError, TypeError):
                fields = []
            for field in fields:
                requirements.append({
                    "field": field,
                    "label": spec.required_label or field,
                    "check": lambda p, f=field: bool(getattr(p, f, None)),
                })
    return requirements


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


def advance_stage(db: Session, plan_id: str, username: str, comment: Optional[str] = None) -> ProductPlan:
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
    transitions = _load_transitions(db)
    allowed = [t for t in transitions if t.from_stage == current.value]
    allowed.sort(key=lambda t: t.sort_order)
    if not allowed:
        raise HTTPException(status_code=400, detail=f"当前阶段「{STAGE_LABELS.get(current, current.value)}」已无下一步")

    # 取第一个合法目标阶段
    target = ProductPlanStage(allowed[0].to_stage)

    # 校验条件（字段级）
    requirements = _load_requirements_for_stage(db, target)
    failures = [req for req in requirements if not req["check"](plan)]
    if failures:
        missing = [f["label"] for f in failures]
        raise HTTPException(
            status_code=400,
            detail=f"推进到「{STAGE_LABELS.get(target, target.value)}」前需要先完成: {'、'.join(missing)}",
        )

    # 校验子表数据条件
    ok, err_msg = _check_stage_requirements(plan, target, db)
    if not ok:
        raise HTTPException(status_code=400, detail=err_msg)

    # 更新状态
    plan.status = target

    # APPROVED → 创建 ApprovalRequest（代替自动生成 Project）
    if target == ProductPlanStage.APPROVED:
        from app.services.product_plan_approval import create_plan_approval
        create_plan_approval(plan.id, db, username, comment=comment)
        # Project 创建将在审批完成后进行

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
                # 审批流程另行处理 plan.approved 事件和 Project 创建
                # 只发射副作用事件（审计+通知）
                event_kwargs["project_id"] = None
                event_kwargs["created_by"] = plan.created_by
                bus.emit_async(EventTypes.PLAN_AUDIT_LOG, **event_kwargs)
                bus.emit_async(EventTypes.PLAN_NOTIFY_PM, **event_kwargs)
            else:
                if target == ProductPlanStage.COMPETITOR:
                    event_kwargs["project_id"] = None
                elif target == ProductPlanStage.RELEASED:
                    event_kwargs["project_id"] = _get_primary_project_id(plan)
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
    transitions = _load_transitions(db)
    allowed = [t for t in transitions if t.from_stage == current.value]
    allowed.sort(key=lambda t: t.sort_order)
    current_label = STAGE_LABELS.get(current, current.value)

    # 当前阶段的检查清单
    current_requirements = _load_requirements_for_stage(db, current)
    missing_current = [req["label"] for req in current_requirements if not req["check"](plan)]

    if not allowed:
        # 已到最后阶段
        return {
            "current_stage": current_label,
            "next_stage": None,
            "next_action": "流程已完成",
            "missing_fields": [],
            "can_advance": False,
        }

    target = ProductPlanStage(allowed[0].to_stage)
    target_label = STAGE_LABELS.get(target, target.value)
    target_requirements = _load_requirements_for_stage(db, target)

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


def _check_stage_requirements(plan: ProductPlan, target: ProductPlanStage, db: Session) -> Tuple[bool, str]:
    """检查推进到下一阶段所需的子表数据条件

    Args:
        plan: 当前产品策划
        target: 目标阶段（由调用方从 DB 规则推导）
        db: 数据库会话

    Returns:
        (is_ok: bool, error_message: str)
    """
    if target == ProductPlanStage.DEFINITION:
        initiation = plan.initiation
        if not initiation or (not initiation.background_basis and not initiation.overall_goal):
            return False, "推进到「产品定义」前需要先填写项目背景或总体目标"
    elif target == ProductPlanStage.COSTING:
        if not plan.costs or len(plan.costs) == 0:
            return False, "推进到「成本目标」前需要至少一条成本记录"
    elif target == ProductPlanStage.TECH_INPUT:
        tech_spec = plan.tech_spec
        if not tech_spec or not tech_spec.core_performance:
            return False, "推进到「技术方案」前需要填写核心技术参数"
    elif target == ProductPlanStage.PROJECT_INIT:
        if not plan.market_info:
            return False, "推进到「立项审批」前需要填写市场与客户需求"
        if not plan.team_members or len(plan.team_members) == 0:
            return False, "推进到「立项审批」前需要至少一名团队成员"

    return True, ""


def _get_primary_project_id(plan) -> Optional[int]:
    """从 project_links 获取第一个 link_type='primary' 的 project_id"""
    for link in (plan.project_links or []):
        if link.link_type == 'primary':
            return link.project_id
    return None


def _generate_project_from_plan(plan: ProductPlan, db: Session, username: str) -> Project:
    """APPROVED 审批通过后生成 Project（将策划数据映射到项目字段）"""
    from datetime import date, timedelta
    import re

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

    # ── 从子表读取关键数据 ──
    initiation = plan.initiation       # ProductPlanInitiation or None
    market_info = plan.market_info     # ProductPlanMarket or None
    tech_spec = plan.tech_spec         # ProductPlanTechSpec or None

    # 构建 description（汇总子表关键信息）
    desc_parts = []
    if initiation:
        parts = []
        for label, val in [
            ("目标市场", initiation.target_market),
            ("产品类型", initiation.product_type),
            ("温带", initiation.climate_zone),
            ("制冷剂", initiation.refrigerant),
            ("覆盖容量", initiation.capacity_range),
            ("电压频率", initiation.voltage_freq),
            ("能效等级", initiation.energy_rating),
            ("客户", initiation.customer_name),
            ("FOB目标价", initiation.fob_price),
            ("BOM成本目标", initiation.bom_cost_target),
            ("年销量预测", initiation.annual_sales_forecast),
            ("产品生命周期", initiation.product_lifecycle),
        ]:
            if val:
                parts.append(f"{label}: {val}")
        if initiation.background_basis:
            parts.append(f"背景: {initiation.background_basis[:200]}")
        if initiation.overall_goal:
            parts.append(f"总体目标: {initiation.overall_goal[:200]}")
        if parts:
            desc_parts.append("【立项信息】" + "; ".join(parts))

    if market_info:
        parts = []
        for label, val in [
            ("主销容量", market_info.main_capacity),
            ("能效要求", market_info.energy_efficiency_req),
            ("目标售价", market_info.target_price),
        ]:
            if val:
                parts.append(f"{label}: {val}")
        if market_info.customer_requirements:
            parts.append(f"客户需求: {market_info.customer_requirements[:200]}")
        if market_info.cert_requirements:
            parts.append(f"认证要求: {market_info.cert_requirements[:200]}")
        if parts:
            desc_parts.append("【市场信息】" + "; ".join(parts))

    if tech_spec:
        parts = []
        if tech_spec.core_performance:
            parts.append(f"核心性能: {tech_spec.core_performance[:200]}")
        if tech_spec.safety_compliance:
            parts.append(f"安全合规: {tech_spec.safety_compliance[:200]}")
        if tech_spec.optional_config:
            parts.append(f"选配要求: {tech_spec.optional_config[:200]}")
        if parts:
            desc_parts.append("【技术要求】" + "; ".join(parts))

    description = "\n".join(desc_parts) if desc_parts else None

    # 计算 start_date / target_end_date
    start_date = today
    target_end_date = None
    if initiation:
        if initiation.required_date:
            target_end_date = initiation.required_date
        elif initiation.project_duration:
            match = re.search(r'(\d+)', initiation.project_duration)
            if match:
                months = int(match.group(1))
                target_month = start_date.month + months
                target_year = start_date.year + (target_month - 1) // 12
                target_month = ((target_month - 1) % 12) + 1
                try:
                    target_end_date = date(target_year, target_month, start_date.day)
                except ValueError:
                    target_end_date = date(target_year, target_month, 28)

    # 融合 market_policy：plan.market + initiation.target_market
    market_policy = plan.market or ""
    if initiation and initiation.target_market:
        if market_policy:
            market_policy += f" / {initiation.target_market}"
        else:
            market_policy = initiation.target_market

    project = Project(
        code=code,
        name=project_name,
        project_class="C级",
        source="产品策划",
        source_category="product_creation",
        status="planning",
        owner=username,
        budget=int(target_cost) if target_cost > 0 else None,
        market_policy=market_policy or None,
        annual_planning_ref=plan.name,
        description=description,
        start_date=start_date,
        target_end_date=target_end_date,
        product_plan_id=plan.id,
    )
    db.add(project)
    db.flush()  # 获取 project.id
    return project
