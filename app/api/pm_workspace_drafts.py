"""PM工作台 — 草稿 CRUD + 提交/退回操作"""
from __future__ import annotations
import json
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.product_plan import ProductPlan, ProductPlanStage, ProductPlanProjectLink
from app.models.product_plan_subs import ProductPlanInitiation, ProductPlanMarket, ProductPlanTechSpec, ProductPlanTeam
from app.api.pm_workspace import _require_pm
from app.api.pm_workspace_utils import _project_to_dict, _apply_project_fields
from app.api.pm_proposal_utils import inject_cooling_capacity_to_core_performance, generate_labor_costs_json
from app.models.approval import ApprovalRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pm", tags=["产品经理工作台"])


@router.post("/project/draft")
def pm_create_draft(
    name: str = Body(..., max_length=200),
    description: str | None = Body(None),
    market_policy: str | None = Body(None, max_length=200),
    annual_planning_ref: str | None = Body(None, max_length=100),
    budget: int | None = Body(None),
    product_code: str | None = Body(None, max_length=50),
    project_class: str = Body("B", pattern="^(T|A|B|C)$"),
    source: str | None = Body(None, max_length=50),
    target_end_date: date | None = Body(None),
    start_date: date | None = Body(None),
    program_id: int | None = Body(None),
    leader_id: int | None = Body(None),
    # Sheet 1 - 项目概述
    product_type: str | None = Body(None, max_length=50),
    target_market: str | None = Body(None, max_length=100),
    climate_zone: str | None = Body(None, max_length=50),
    refrigerant: str | None = Body(None, max_length=50),
    capacity_range: str | None = Body(None, max_length=100),
    voltage_freq: str | None = Body(None, max_length=50),
    series_name: str | None = Body(None, max_length=50),
    energy_rating: str | None = Body(None, max_length=20),
    ip_ownership: str | None = Body(None, max_length=100),
    project_duration: str | None = Body(None, max_length=50),
    dev_category: str | None = Body(None, max_length=50),
    project_origin: str | None = Body(None, max_length=100),
    background_basis: str | None = Body(None),
    overall_goal: str | None = Body(None),
    tech_goal: str | None = Body(None),
    cost_goal: str | None = Body(None),
    sales_goal: str | None = Body(None),
    cert_goal: str | None = Body(None),
    schedule_goal: str | None = Body(None),
    patent_goal: str | None = Body(None),
    other_goals: str | None = Body(None),
    deliverables: str | None = Body(None),
    sample_qty: int | None = Body(None),
    required_date: date | None = Body(None),
    # Sheet 2 - 市场与客户需求
    main_capacity: str | None = Body(None, max_length=50),
    energy_efficiency_req: str | None = Body(None, max_length=100),
    cert_requirements: str | None = Body(None),
    target_price: str | None = Body(None, max_length=50),
    customer_requirements: str | None = Body(None),
    # Sheet 3 - 技术要求
    core_performance: str | None = Body(None),
    safety_compliance: str | None = Body(None),
    optional_config: str | None = Body(None),
    # Sheet 4 - 成本核算
    dev_cost_items: str | None = Body(None),
    economic_indicators: str | None = Body(None),
    mold_costs: str | None = Body(None),
    prototype_costs_detail: str | None = Body(None),
    test_costs: str | None = Body(None),
    cert_costs: str | None = Body(None),
    # Sheet 5 - 团队与职责
    team_members: str | None = Body(None),
    # Sheet 4/5 extended - 新Excel字段
    customer_name: str | None = Body(None, max_length=100),
    other_requirements: str | None = Body(None),
    accessory_config: str | None = Body(None),
    feature_config: str | None = Body(None),
    fob_price: str | None = Body(None, max_length=50),
    bom_cost_target: str | None = Body(None, max_length=50),
    bom_cost_ratio: str | None = Body(None, max_length=50),
    manufacturing_cost: str | None = Body(None, max_length=50),
    gross_margin: str | None = Body(None, max_length=50),
    annual_sales_forecast: str | None = Body(None, max_length=50),
    product_lifecycle: str | None = Body(None, max_length=50),
    mold_inner: str | None = Body(None),
    mold_outer: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """PM 保存草稿项目 — is_draft=True, status='draft'"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    p = Project(
        name=name.strip(), project_class=project_class, owner=current_user.username,
        status="draft", is_draft=True, program_id=program_id, leader_id=leader_id,
    )
    db.add(p)
    db.flush()

    plan = ProductPlan(name=p.name, status=ProductPlanStage.DRAFT, created_by=current_user.username)
    db.add(plan)
    db.flush()

    existing = db.query(ProductPlanProjectLink).filter(ProductPlanProjectLink.project_id == p.id).first()
    if existing:
        existing.link_type = 'primary'
    else:
        db.add(ProductPlanProjectLink(product_plan_id=plan.id, project_id=p.id, link_type='primary'))

    init = ProductPlanInitiation(product_plan_id=plan.id)
    market = ProductPlanMarket(product_plan_id=plan.id)
    tech = ProductPlanTechSpec(product_plan_id=plan.id)
    db.add(init)
    db.add(market)
    db.add(tech)

    _apply_project_fields(p, name=name, description=description, market_policy=market_policy,
        annual_planning_ref=annual_planning_ref, budget=budget, product_code=product_code,
        project_class=project_class, source=source, target_end_date=target_end_date,
        start_date=start_date, program_id=program_id, leader_id=leader_id,
        product_type=product_type, target_market=target_market, climate_zone=climate_zone,
        refrigerant=refrigerant, capacity_range=capacity_range, voltage_freq=voltage_freq,
        series_name=series_name, energy_rating=energy_rating, ip_ownership=ip_ownership,
        project_duration=project_duration, dev_category=dev_category, project_origin=project_origin,
        background_basis=background_basis, overall_goal=overall_goal, tech_goal=tech_goal,
        cost_goal=cost_goal, sales_goal=sales_goal, cert_goal=cert_goal, schedule_goal=schedule_goal,
        patent_goal=patent_goal, other_goals=other_goals, deliverables=deliverables,
        sample_qty=sample_qty, required_date=required_date, main_capacity=main_capacity,
        energy_efficiency_req=energy_efficiency_req, cert_requirements=cert_requirements,
        target_price=target_price, customer_requirements=customer_requirements,
        core_performance=core_performance, safety_compliance=safety_compliance,
        optional_config=optional_config, dev_cost_items=dev_cost_items,
        economic_indicators=economic_indicators, mold_costs=mold_costs,
        prototype_costs_detail=prototype_costs_detail, test_costs=test_costs,
        cert_costs=cert_costs, team_members=team_members, customer_name=customer_name,
        other_requirements=other_requirements, accessory_config=accessory_config,
        feature_config=feature_config, fob_price=fob_price, bom_cost_target=bom_cost_target,
        bom_cost_ratio=bom_cost_ratio, manufacturing_cost=manufacturing_cost,
        gross_margin=gross_margin, annual_sales_forecast=annual_sales_forecast,
        product_lifecycle=product_lifecycle, mold_inner=mold_inner, mold_outer=mold_outer)

    # 自动计算：制冷量 BTU → 瓦特
    if capacity_range and plan.tech_spec:
        plan.tech_spec.core_performance = inject_cooling_capacity_to_core_performance(plan.tech_spec.core_performance, capacity_range)
    # 自动计算：人月费用
    if project_duration or team_members:
        plan.initiation.labor_costs = generate_labor_costs_json(project_duration, team_members)

    try:
        db.commit()
        db.refresh(p)
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        logger.error(f"PM工作台草稿项目保存失败: {e}")
        raise

    return _project_to_dict(p)


@router.put("/project/draft/{pid}")
def pm_update_draft(
    pid: int,
    name: str | None = Body(None, max_length=200),
    description: str | None = Body(None),
    market_policy: str | None = Body(None, max_length=200),
    annual_planning_ref: str | None = Body(None, max_length=100),
    budget: int | None = Body(None),
    product_code: str | None = Body(None, max_length=50),
    project_class: str | None = Body(None, pattern="^(T|A|B|C)$"),
    source: str | None = Body(None, max_length=50),
    target_end_date: date | None = Body(None),
    program_id: int | None = Body(None),
    leader_id: int | None = Body(None),
    # Sheet 1 - 项目概述
    product_type: str | None = Body(None, max_length=50),
    target_market: str | None = Body(None, max_length=100),
    climate_zone: str | None = Body(None, max_length=50),
    refrigerant: str | None = Body(None, max_length=50),
    capacity_range: str | None = Body(None, max_length=100),
    voltage_freq: str | None = Body(None, max_length=50),
    series_name: str | None = Body(None, max_length=50),
    energy_rating: str | None = Body(None, max_length=20),
    ip_ownership: str | None = Body(None, max_length=100),
    project_duration: str | None = Body(None, max_length=50),
    dev_category: str | None = Body(None, max_length=50),
    project_origin: str | None = Body(None, max_length=100),
    background_basis: str | None = Body(None),
    overall_goal: str | None = Body(None),
    tech_goal: str | None = Body(None),
    cost_goal: str | None = Body(None),
    sales_goal: str | None = Body(None),
    cert_goal: str | None = Body(None),
    schedule_goal: str | None = Body(None),
    patent_goal: str | None = Body(None),
    other_goals: str | None = Body(None),
    deliverables: str | None = Body(None),
    sample_qty: int | None = Body(None),
    required_date: date | None = Body(None),
    # Sheet 2 - 市场与客户需求
    main_capacity: str | None = Body(None, max_length=50),
    energy_efficiency_req: str | None = Body(None, max_length=100),
    cert_requirements: str | None = Body(None),
    target_price: str | None = Body(None, max_length=50),
    customer_requirements: str | None = Body(None),
    # Sheet 3 - 技术要求
    core_performance: str | None = Body(None),
    safety_compliance: str | None = Body(None),
    optional_config: str | None = Body(None),
    # Sheet 4 - 成本核算
    dev_cost_items: str | None = Body(None),
    economic_indicators: str | None = Body(None),
    mold_costs: str | None = Body(None),
    prototype_costs_detail: str | None = Body(None),
    test_costs: str | None = Body(None),
    cert_costs: str | None = Body(None),
    # Sheet 5 - 团队与职责
    team_members: str | None = Body(None),
    # Sheet 4/5 extended
    customer_name: str | None = Body(None, max_length=100),
    other_requirements: str | None = Body(None),
    accessory_config: str | None = Body(None),
    feature_config: str | None = Body(None),
    fob_price: str | None = Body(None, max_length=50),
    bom_cost_target: str | None = Body(None, max_length=50),
    bom_cost_ratio: str | None = Body(None, max_length=50),
    manufacturing_cost: str | None = Body(None, max_length=50),
    gross_margin: str | None = Body(None, max_length=50),
    annual_sales_forecast: str | None = Body(None, max_length=50),
    product_lifecycle: str | None = Body(None, max_length=50),
    mold_inner: str | None = Body(None),
    mold_outer: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """PM 更新草稿项目 — 仅 owner 本人可编辑"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可更新此项目")
    if not p.is_draft:
        raise HTTPException(status_code=400, detail="已提交或审批中的项目不可编辑，如需修改请撤回审批")

    try:
        _apply_project_fields(p, name=name, description=description, market_policy=market_policy,
            annual_planning_ref=annual_planning_ref, budget=budget, product_code=product_code,
            project_class=project_class, source=source, target_end_date=target_end_date,
            start_date=start_date, program_id=program_id, leader_id=leader_id,
            product_type=product_type, target_market=target_market, climate_zone=climate_zone,
            refrigerant=refrigerant, capacity_range=capacity_range, voltage_freq=voltage_freq,
            series_name=series_name, energy_rating=energy_rating, ip_ownership=ip_ownership,
            project_duration=project_duration, dev_category=dev_category, project_origin=project_origin,
            background_basis=background_basis, overall_goal=overall_goal, tech_goal=tech_goal,
            cost_goal=cost_goal, sales_goal=sales_goal, cert_goal=cert_goal, schedule_goal=schedule_goal,
            patent_goal=patent_goal, other_goals=other_goals, deliverables=deliverables,
            sample_qty=sample_qty, required_date=required_date, main_capacity=main_capacity,
            energy_efficiency_req=energy_efficiency_req, cert_requirements=cert_requirements,
            target_price=target_price, customer_requirements=customer_requirements,
            core_performance=core_performance, safety_compliance=safety_compliance,
            optional_config=optional_config, dev_cost_items=dev_cost_items,
            economic_indicators=economic_indicators, mold_costs=mold_costs,
            prototype_costs_detail=prototype_costs_detail, test_costs=test_costs,
            cert_costs=cert_costs, team_members=team_members, customer_name=customer_name,
            other_requirements=other_requirements, accessory_config=accessory_config,
            feature_config=feature_config, fob_price=fob_price, bom_cost_target=bom_cost_target,
            bom_cost_ratio=bom_cost_ratio, manufacturing_cost=manufacturing_cost,
            gross_margin=gross_margin, annual_sales_forecast=annual_sales_forecast,
            product_lifecycle=product_lifecycle, mold_inner=mold_inner, mold_outer=mold_outer)

        # 自动计算：制冷量 BTU → 瓦特
        link = next((link for link in (p.product_plan_links or []) if link.link_type == 'primary'), None)
        plan = link.product_plan if link else None
        if capacity_range and plan and plan.tech_spec:
            plan.tech_spec.core_performance = inject_cooling_capacity_to_core_performance(plan.tech_spec.core_performance, capacity_range)
        # 自动计算：人月费用
        if project_duration is not None or team_members is not None:
            if plan and plan.initiation:
                plan.initiation.labor_costs = generate_labor_costs_json(
                    project_duration if project_duration is not None else plan.initiation.project_duration,
                    team_members if team_members is not None else None,
                )

        db.commit()
        db.refresh(p)
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        logger.error(f"PM更新草稿项目失败: {e}")
        raise

    return _project_to_dict(p)


@router.post("/proposals/submit")
def submit_proposal(
    project_id: int = Body(..., description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """提交项目立项 — 推进关联 ProductPlan 到 PROJECT_INIT 并创建审批请求"""
    p = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可提交立项")

    link = db.query(ProductPlanProjectLink).filter(
        ProductPlanProjectLink.project_id == p.id, ProductPlanProjectLink.link_type == 'primary'
    ).first()
    plan_id = link.product_plan_id if link else None
    if not plan_id:
        raise HTTPException(status_code=400, detail="项目未关联产品策划，无法提交审批")

    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="关联的产品策划不存在")

    from app.services.product_plan_workflow import advance_stage

    stage_order = [
        ProductPlanStage.DRAFT, ProductPlanStage.COMPETITOR, ProductPlanStage.DEFINITION,
        ProductPlanStage.COSTING, ProductPlanStage.TECH_INPUT, ProductPlanStage.PROJECT_INIT,
    ]
    target_stage = ProductPlanStage.PROJECT_INIT
    current = plan.status

    if current in stage_order:
        current_idx = stage_order.index(current)
        target_idx = stage_order.index(target_stage)
        if current_idx < target_idx:
            for step in range(current_idx, target_idx):
                plan = advance_stage(db, plan_id, current_user.username)
        elif current_idx > target_idx:
            raise HTTPException(status_code=400, detail=f"产品策划已超出立项阶段（当前: {ProductPlanStage.PROJECT_INIT.value}），无法重复提交")

    p.is_draft = False
    p.approval_status = "pending"
    db.flush()

    from app.services.product_plan_approval import create_plan_approval
    approval = create_plan_approval(plan_id, db, current_user.username)

    return {"plan_id": plan_id, "plan_status": plan.status.value, "approval_id": approval.id, "message": "项目已提交审批"}


@router.post("/proposals/{proposal_id}/withdraw")
def withdraw_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """撤回立项审批请求 — 仅申请人可撤回"""
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == proposal_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    if req.requester != current_user.username:
        raise HTTPException(status_code=403, detail="仅申请人可撤回审批")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"当前审批状态为「{req.status}」，无法撤回")

    req.status = "withdrawn"

    if req.request_type == "product_plan":
        plan_id = None
        if req.step_meta:
            try:
                meta = json.loads(req.step_meta) if isinstance(req.step_meta, str) else req.step_meta
                plan_id = meta.get("plan_id")
            except (json.JSONDecodeError, TypeError):
                pass
        if plan_id:
            plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
            if plan and plan.status == ProductPlanStage.PROJECT_INIT:
                plan.status = ProductPlanStage.TECH_INPUT

    db.commit()
    return {"id": req.id, "status": req.status, "message": "审批已撤回"}
