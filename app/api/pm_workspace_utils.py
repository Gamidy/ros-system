"""PM工作台共享辅助函数 — _project_to_dict / _apply_project_fields"""
from __future__ import annotations
import json
from typing import Any
from app.models.project import Project
from app.models.product_plan import ProductPlanProjectLink
from app.models.product_plan_subs import ProductPlanInitiation, ProductPlanMarket, ProductPlanTechSpec, ProductPlanTeam


def _project_to_dict(p: Project) -> dict:
    """将 Project ORM 对象转为包含所有 Initiation 字段的 dict"""
    init = None
    market = None
    tech = None
    team_list = None
    link = next((link for link in p.product_plan_links if link.link_type == 'primary'), None)
    if link:
        plan = link.product_plan
        if plan:
            init = plan.initiation
            market = plan.market_info
            tech = plan.tech_spec
            team_list = plan.team_members

    def _v(obj, attr, default=None) -> Any:
        return getattr(obj, attr, default) if obj else default

    return {
        "id": p.id, "code": p.code, "name": p.name, "project_class": p.project_class,
        "source": p.source, "source_category": p.source_category, "product_code": p.product_code,
        "status": p.status, "start_date": str(p.start_date) if p.start_date else None,
        "target_end_date": str(p.target_end_date) if p.target_end_date else None,
        "actual_end_date": str(p.actual_end_date) if p.actual_end_date else None,
        "owner": p.owner, "description": p.description, "critical_path": p.critical_path,
        "market_policy": p.market_policy, "annual_planning_ref": p.annual_planning_ref,
        "budget": p.budget, "program_id": p.program_id, "leader_id": p.leader_id,
        "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
        # Sheet 1 - 项目概述
        "product_type": _v(init, "product_type"), "target_market": _v(init, "target_market"),
        "climate_zone": _v(init, "climate_zone"), "refrigerant": _v(init, "refrigerant"),
        "capacity_range": _v(init, "capacity_range"), "voltage_freq": _v(init, "voltage_freq"),
        "series_name": _v(init, "series_name"), "energy_rating": _v(init, "energy_rating"),
        "ip_ownership": _v(init, "ip_ownership"), "project_duration": _v(init, "project_duration"),
        "dev_category": _v(init, "dev_category"), "project_origin": _v(init, "project_origin"),
        "background_basis": _v(init, "background_basis"), "overall_goal": _v(init, "overall_goal"),
        "tech_goal": _v(init, "tech_goal"), "cost_goal": _v(init, "cost_goal"),
        "sales_goal": _v(init, "sales_goal"), "cert_goal": _v(init, "cert_goal"),
        "schedule_goal": _v(init, "schedule_goal"), "patent_goal": _v(init, "patent_goal"),
        "other_goals": _v(init, "other_goals"), "deliverables": _v(init, "deliverables"),
        "sample_qty": _v(init, "sample_qty"),
        "required_date": str(_v(init, "required_date")) if _v(init, "required_date") else None,
        # Sheet 2 - 市场与客户需求
        "main_capacity": _v(market, "main_capacity"),
        "energy_efficiency_req": _v(market, "energy_efficiency_req"),
        "cert_requirements": _v(market, "cert_requirements"),
        "target_price": _v(market, "target_price"),
        "customer_requirements": _v(market, "customer_requirements"),
        # Sheet 3 - 技术要求
        "core_performance": _v(tech, "core_performance"),
        "safety_compliance": _v(tech, "safety_compliance"),
        "optional_config": _v(tech, "optional_config"),
        # Sheet 4 - 成本核算
        "dev_cost_items": _v(init, "dev_cost_items"),
        "economic_indicators": _v(init, "economic_indicators"),
        "mold_costs": _v(init, "mold_costs"),
        "prototype_costs_detail": _v(init, "prototype_costs_detail"),
        "test_costs": _v(init, "test_costs"), "cert_costs": _v(init, "cert_costs"),
        "labor_costs": _v(init, "labor_costs"),
        # Sheet 5 - 团队
        "team_members": json.dumps([{
            "role_name": t.role_name, "member_name": t.member_name,
            "department": t.department, "responsibility": t.responsibility,
        } for t in (team_list or [])], ensure_ascii=False) if team_list else None,
        # New fields (Excel alignment)
        "customer_name": _v(init, "customer_name"),
        "other_requirements": _v(init, "other_requirements"),
        "accessory_config": _v(init, "accessory_config"),
        "feature_config": _v(init, "feature_config"),
        "fob_price": _v(init, "fob_price"), "bom_cost_target": _v(init, "bom_cost_target"),
        "bom_cost_ratio": _v(init, "bom_cost_ratio"),
        "manufacturing_cost": _v(init, "manufacturing_cost"),
        "gross_margin": _v(init, "gross_margin"),
        "annual_sales_forecast": _v(init, "annual_sales_forecast"),
        "product_lifecycle": _v(init, "product_lifecycle"),
        "mold_inner": _v(init, "mold_inner"), "mold_outer": _v(init, "mold_outer"),
        # Draft
        "is_draft": p.is_draft, "created_at": str(p.created_at) if p.created_at else None,
        "updated_at": str(p.updated_at) if p.updated_at else None,
    }


def _apply_project_fields(
    p: Project,
    name: str | None = None, description: str | None = None,
    market_policy: str | None = None, annual_planning_ref: str | None = None,
    budget: int | None = None, product_code: str | None = None,
    project_class: str | None = None, source: str | None = None,
    target_end_date: Any = None, start_date: Any = None,
    program_id: int | None = None, leader_id: int | None = None,
    # Sheet 1
    product_type: str | None = None, target_market: str | None = None,
    climate_zone: str | None = None, refrigerant: str | None = None,
    capacity_range: str | None = None, voltage_freq: str | None = None,
    series_name: str | None = None, energy_rating: str | None = None,
    ip_ownership: str | None = None, project_duration: str | None = None,
    dev_category: str | None = None, project_origin: str | None = None,
    background_basis: str | None = None, overall_goal: str | None = None,
    tech_goal: str | None = None, cost_goal: str | None = None,
    sales_goal: str | None = None, cert_goal: str | None = None,
    schedule_goal: str | None = None, patent_goal: str | None = None,
    other_goals: str | None = None, deliverables: str | None = None,
    sample_qty: int | None = None, required_date: Any = None,
    # Sheet 2
    main_capacity: str | None = None, energy_efficiency_req: str | None = None,
    cert_requirements: str | None = None, target_price: str | None = None,
    customer_requirements: str | None = None,
    # Sheet 3
    core_performance: str | None = None, safety_compliance: str | None = None,
    optional_config: str | None = None,
    # Sheet 4
    dev_cost_items: str | None = None, economic_indicators: str | None = None,
    mold_costs: str | None = None, prototype_costs_detail: str | None = None,
    test_costs: str | None = None, cert_costs: str | None = None,
    labor_costs: str | None = None,
    # New fields
    customer_name: str | None = None, other_requirements: str | None = None,
    accessory_config: str | None = None, feature_config: str | None = None,
    fob_price: str | None = None, bom_cost_target: str | None = None,
    bom_cost_ratio: str | None = None, manufacturing_cost: str | None = None,
    gross_margin: str | None = None, annual_sales_forecast: str | None = None,
    product_lifecycle: str | None = None, mold_inner: str | None = None,
    mold_outer: str | None = None,
    # Sheet 5
    team_members: str | None = None,
) -> None:
    """将非 None 参数写入 Project 对象（基础字段直接写，Sheet1-5 写 ProductPlan 子表）"""
    # ---- 基础 Project 字段 ----
    if name is not None: p.name = name.strip()
    if description is not None: p.description = description
    if market_policy is not None: p.market_policy = market_policy
    if annual_planning_ref is not None: p.annual_planning_ref = annual_planning_ref
    if budget is not None: p.budget = budget
    if product_code is not None: p.product_code = product_code
    if project_class is not None: p.project_class = project_class
    if source is not None: p.source = source
    if target_end_date is not None: p.target_end_date = target_end_date
    if start_date is not None: p.start_date = start_date
    if program_id is not None: p.program_id = program_id
    if leader_id is not None: p.leader_id = leader_id

    # ---- Sheet1-5 字段写入 ProductPlan 子表 ----
    link = next((link for link in p.product_plan_links if link.link_type == 'primary'), None)
    plan = link.product_plan if link else None
    if plan is None:
        return

    if not plan.initiation:
        plan.initiation = ProductPlanInitiation(product_plan_id=plan.id)
    if not plan.market_info:
        plan.market_info = ProductPlanMarket(product_plan_id=plan.id)
    if not plan.tech_spec:
        plan.tech_spec = ProductPlanTechSpec(product_plan_id=plan.id)

    init = plan.initiation
    market = plan.market_info
    tech = plan.tech_spec

    # Sheet 1 → ProductPlanInitiation
    if product_type is not None: init.product_type = product_type
    if target_market is not None: init.target_market = target_market
    if climate_zone is not None: init.climate_zone = climate_zone
    if refrigerant is not None: init.refrigerant = refrigerant
    if capacity_range is not None: init.capacity_range = capacity_range
    if voltage_freq is not None: init.voltage_freq = voltage_freq
    if series_name is not None: init.series_name = series_name
    if energy_rating is not None: init.energy_rating = energy_rating
    if ip_ownership is not None: init.ip_ownership = ip_ownership
    if project_duration is not None: init.project_duration = project_duration
    if dev_category is not None: init.dev_category = dev_category
    if project_origin is not None: init.project_origin = project_origin
    if background_basis is not None: init.background_basis = background_basis
    if overall_goal is not None: init.overall_goal = overall_goal
    if tech_goal is not None: init.tech_goal = tech_goal
    if cost_goal is not None: init.cost_goal = cost_goal
    if sales_goal is not None: init.sales_goal = sales_goal
    if cert_goal is not None: init.cert_goal = cert_goal
    if schedule_goal is not None: init.schedule_goal = schedule_goal
    if patent_goal is not None: init.patent_goal = patent_goal
    if other_goals is not None: init.other_goals = other_goals
    if deliverables is not None: init.deliverables = deliverables
    if sample_qty is not None: init.sample_qty = sample_qty
    if required_date is not None: init.required_date = required_date

    # Sheet 2 → ProductPlanMarket
    if main_capacity is not None: market.main_capacity = main_capacity
    if energy_efficiency_req is not None: market.energy_efficiency_req = energy_efficiency_req
    if cert_requirements is not None: market.cert_requirements = cert_requirements
    if target_price is not None: market.target_price = target_price
    if customer_requirements is not None: market.customer_requirements = customer_requirements

    # Sheet 3 → ProductPlanTechSpec
    if core_performance is not None: tech.core_performance = core_performance
    if safety_compliance is not None: tech.safety_compliance = safety_compliance
    if optional_config is not None: tech.optional_config = optional_config

    # Sheet 4 (costs) → ProductPlanInitiation
    if dev_cost_items is not None: init.dev_cost_items = dev_cost_items
    if economic_indicators is not None: init.economic_indicators = economic_indicators
    if mold_costs is not None: init.mold_costs = mold_costs
    if prototype_costs_detail is not None: init.prototype_costs_detail = prototype_costs_detail
    if test_costs is not None: init.test_costs = test_costs
    if cert_costs is not None: init.cert_costs = cert_costs
    if labor_costs is not None: init.labor_costs = labor_costs

    # New fields → ProductPlanInitiation
    if customer_name is not None: init.customer_name = customer_name
    if other_requirements is not None: init.other_requirements = other_requirements
    if accessory_config is not None: init.accessory_config = accessory_config
    if feature_config is not None: init.feature_config = feature_config
    if fob_price is not None: init.fob_price = fob_price
    if bom_cost_target is not None: init.bom_cost_target = bom_cost_target
    if bom_cost_ratio is not None: init.bom_cost_ratio = bom_cost_ratio
    if manufacturing_cost is not None: init.manufacturing_cost = manufacturing_cost
    if gross_margin is not None: init.gross_margin = gross_margin
    if annual_sales_forecast is not None: init.annual_sales_forecast = annual_sales_forecast
    if product_lifecycle is not None: init.product_lifecycle = product_lifecycle
    if mold_inner is not None: init.mold_inner = mold_inner
    if mold_outer is not None: init.mold_outer = mold_outer

    # Sheet 5 (team) → ProductPlanTeam (1:N, 替换策略)
    if team_members is not None:
        for old_t in list(plan.team_members):
            plan.team_members.remove(old_t)
        try:
            members = json.loads(team_members) if isinstance(team_members, str) else team_members
            if isinstance(members, list):
                for m in members:
                    plan.team_members.append(ProductPlanTeam(
                        product_plan_id=plan.id,
                        role_name=m.get("role_name", ""),
                        member_name=m.get("member_name"),
                        department=m.get("department"),
                        responsibility=m.get("responsibility"),
                    ))
        except (json.JSONDecodeError, TypeError):
            pass
