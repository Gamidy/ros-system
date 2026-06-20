"""产品经理(PM)工作台API — 聚合视图 + 快捷CRUD + Product Initiation Draft 管理

提供 PM 角色专属的项目管理工作台:
- GET  /api/pm/workspace      — 聚合面板数据
- POST /api/pm/project        — 一站式快捷创建项目 (正式)
- POST /api/pm/project/draft  — 保存草稿项目
- PUT  /api/pm/project/draft/{pid} — 更新草稿项目
- POST /api/pm/project/submit/{pid} — 草稿提交为正式项目
- PATCH /api/pm/project/{pid} — 快捷更新项目字段
"""
from datetime import datetime, date
import json
import random
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project, Program
from app.models.product import Product, Platform
from app.schemas import ProjectCreate, ProjectOut
from app.api.pm_proposal_utils import (
    calc_cooling_capacity_btu_to_w,
    inject_cooling_capacity_to_core_performance,
    generate_labor_costs_json,
    get_cert_costs_from_compliance,
    generate_project_name,
)

router = APIRouter(prefix="/pm", tags=["产品经理工作台"])


# ══════════════════════════════════════════════════════════════
# 角色守卫 — 仅 product_manager 可访问
# ══════════════════════════════════════════════════════════════

def _require_pm(current_user: User = Depends(get_current_user)) -> User:
    """校验当前用户为 product_manager 角色"""
    if current_user.role != "product_manager":
        raise HTTPException(status_code=403, detail="仅产品经理可访问此接口")
    return current_user


# ══════════════════════════════════════════════════════════════
# 辅助: 构建项目返回字典（包含所有新字段）
# ══════════════════════════════════════════════════════════════

def _project_to_dict(p: Project) -> dict:
    """将 Project ORM 对象转为包含所有 Initiation 字段的 dict"""
    return {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "project_class": p.project_class,
        "source": p.source,
        "source_category": p.source_category,
        "product_code": p.product_code,
        "status": p.status,
        "start_date": str(p.start_date) if p.start_date else None,
        "target_end_date": str(p.target_end_date) if p.target_end_date else None,
        "actual_end_date": str(p.actual_end_date) if p.actual_end_date else None,
        "owner": p.owner,
        "description": p.description,
        "critical_path": p.critical_path,
        "market_policy": p.market_policy,
        "annual_planning_ref": p.annual_planning_ref,
        "budget": p.budget,
        "program_id": p.program_id,
        "leader_id": p.leader_id,
        "dev_modules": p.dev_modules,
        "change_impacts": p.change_impacts,
        # Sheet 1 - 项目概述
        "product_type": p.product_type,
        "target_market": p.target_market,
        "climate_zone": p.climate_zone,
        "refrigerant": p.refrigerant,
        "capacity_range": p.capacity_range,
        "voltage_freq": p.voltage_freq,
        "series_name": p.series_name,
        "energy_rating": p.energy_rating,
        "ip_ownership": p.ip_ownership,
        "project_duration": p.project_duration,
        "dev_category": p.dev_category,
        "project_origin": p.project_origin,
        "background_basis": p.background_basis,
        "overall_goal": p.overall_goal,
        "tech_goal": p.tech_goal,
        "cost_goal": p.cost_goal,
        "sales_goal": p.sales_goal,
        "cert_goal": p.cert_goal,
        "schedule_goal": p.schedule_goal,
        "patent_goal": p.patent_goal,
        "other_goals": p.other_goals,
        "deliverables": p.deliverables,
        "sample_qty": p.sample_qty,
        "required_date": str(p.required_date) if p.required_date else None,
        # Sheet 2 - 市场与客户需求
        "main_capacity": p.main_capacity,
        "energy_efficiency_req": p.energy_efficiency_req,
        "cert_requirements": p.cert_requirements,
        "target_price": p.target_price,
        "customer_requirements": p.customer_requirements,
        # Sheet 3 - 技术要求
        "core_performance": p.core_performance,
        "safety_compliance": p.safety_compliance,
        "optional_config": p.optional_config,
        # Sheet 4 - 成本核算
        "dev_cost_items": p.dev_cost_items,
        "economic_indicators": p.economic_indicators,
        "mold_costs": p.mold_costs,
        "prototype_costs_detail": p.prototype_costs_detail,
        "test_costs": p.test_costs,
        "cert_costs": p.cert_costs,
        "labor_costs": p.labor_costs,
        # Sheet 5 - 团队与职责
        "team_members": p.team_members,
        # New fields (Excel alignment)
        "customer_name": p.customer_name,
        "other_requirements": p.other_requirements,
        "accessory_config": p.accessory_config,
        "feature_config": p.feature_config,
        "fob_price": p.fob_price,
        "bom_cost_target": p.bom_cost_target,
        "bom_cost_ratio": p.bom_cost_ratio,
        "manufacturing_cost": p.manufacturing_cost,
        "gross_margin": p.gross_margin,
        "annual_sales_forecast": p.annual_sales_forecast,
        "product_lifecycle": p.product_lifecycle,
        "mold_inner": p.mold_inner,
        "mold_outer": p.mold_outer,
        # Draft
        "is_draft": p.is_draft,
        "created_at": str(p.created_at) if p.created_at else None,
        "updated_at": str(p.updated_at) if p.updated_at else None,
    }


# ══════════════════════════════════════════════════════════════
# GET /api/pm/programs — 项目群列表 (供立项选择)
# ══════════════════════════════════════════════════════════════

@router.get("/programs")
def list_active_programs(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """返回所有活跃项目群，供立项时选择"""
    programs = db.query(Program).filter(Program.status == "active").all()
    return [{"id": p.id, "name": p.name, "code": p.code} for p in programs]


# ══════════════════════════════════════════════════════════════
# GET /api/pm/workspace — PM 工作台聚合面板
# ══════════════════════════════════════════════════════════════

@router.get("/workspace")
def pm_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """返回 PM 工作台聚合数据"""
    owner_name = current_user.username

    # ── 我的项目 ──
    my_projects_query = db.query(Project).filter(Project.owner == owner_name)
    my_projects_raw = my_projects_query.order_by(Project.created_at.desc()).all()

    my_projects = []
    total_budget = 0
    completed_count = 0
    overdue_count = 0
    today = date.today()

    for p in my_projects_raw:
        my_projects.append(_project_to_dict(p))
        if p.budget:
            total_budget += p.budget
        if p.status == "completed":
            completed_count += 1
        # 判断逾期: 未完成 且 target_end_date < 今天
        if p.status not in ("completed", "cancelled") and p.target_end_date and p.target_end_date < today:
            overdue_count += 1

    # ── 产品列表 ──
    products_raw = db.query(Product).order_by(Product.created_at.desc()).all()
    products = []
    for prod in products_raw:
        products.append({
            "id": prod.id,
            "code": prod.code,
            "name": prod.name,
            "status": prod.status,
            "capacity": prod.capacity,
            "platform_id": prod.platform_id,
        })

    # ── 统计 ──
    total_projects = len(my_projects_raw)
    active_projects = sum(1 for p in my_projects_raw if p.status not in ("completed", "cancelled"))

    stats = {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_budget": total_budget,
        "completed_count": completed_count,
        "overdue_count": overdue_count,
    }

    # ── 年度规划去重列表 ──
    annual_plans = list(dict.fromkeys(
        p.annual_planning_ref for p in my_projects_raw if p.annual_planning_ref
    ))

    # ── 最近5个项目 ──
    recent_projects = my_projects[:5] if len(my_projects) > 5 else my_projects

    return {
        "my_projects": my_projects,
        "products": products,
        "stats": stats,
        "planning_items": annual_plans,
        "recent_projects": recent_projects,
    }


# ══════════════════════════════════════════════════════════════
# 辅助: _apply_project_fields — 将 Body 参数写入 Project 对象
# ══════════════════════════════════════════════════════════════

def _apply_project_fields(
    p: Project,
    name: str | None = None,
    description: str | None = None,
    market_policy: str | None = None,
    annual_planning_ref: str | None = None,
    budget: int | None = None,
    product_code: str | None = None,
    project_class: str | None = None,
    source: str | None = None,
    target_end_date: date | None = None,
    start_date: date | None = None,
    program_id: int | None = None,
    leader_id: int | None = None,
    # Sheet 1
    product_type: str | None = None,
    target_market: str | None = None,
    climate_zone: str | None = None,
    refrigerant: str | None = None,
    capacity_range: str | None = None,
    voltage_freq: str | None = None,
    series_name: str | None = None,
    energy_rating: str | None = None,
    ip_ownership: str | None = None,
    project_duration: str | None = None,
    dev_category: str | None = None,
    project_origin: str | None = None,
    background_basis: str | None = None,
    overall_goal: str | None = None,
    tech_goal: str | None = None,
    cost_goal: str | None = None,
    sales_goal: str | None = None,
    cert_goal: str | None = None,
    schedule_goal: str | None = None,
    patent_goal: str | None = None,
    other_goals: str | None = None,
    deliverables: str | None = None,
    sample_qty: int | None = None,
    required_date: date | None = None,
    # Sheet 2
    main_capacity: str | None = None,
    energy_efficiency_req: str | None = None,
    cert_requirements: str | None = None,
    target_price: str | None = None,
    customer_requirements: str | None = None,
    # Sheet 3
    core_performance: str | None = None,
    safety_compliance: str | None = None,
    optional_config: str | None = None,
    # Sheet 4
    dev_cost_items: str | None = None,
    economic_indicators: str | None = None,
    mold_costs: str | None = None,
    prototype_costs_detail: str | None = None,
    test_costs: str | None = None,
    labor_costs: str | None = None,
    # New fields (Excel alignment)
    customer_name: str | None = None,
    other_requirements: str | None = None,
    accessory_config: str | None = None,
    feature_config: str | None = None,
    fob_price: str | None = None,
    bom_cost_target: str | None = None,
    bom_cost_ratio: str | None = None,
    manufacturing_cost: str | None = None,
    gross_margin: str | None = None,
    annual_sales_forecast: str | None = None,
    product_lifecycle: str | None = None,
    mold_inner: str | None = None,
    mold_outer: str | None = None,
    # Sheet 5
    team_members: str | None = None,
):
    """将非 None 参数写入 Project 对象（is not None 判断）"""
    if name is not None:
        p.name = name.strip()
    if description is not None:
        p.description = description
    if market_policy is not None:
        p.market_policy = market_policy
    if annual_planning_ref is not None:
        p.annual_planning_ref = annual_planning_ref
    if budget is not None:
        p.budget = budget
    if product_code is not None:
        p.product_code = product_code
    if project_class is not None:
        p.project_class = project_class
    if source is not None:
        p.source = source
    if target_end_date is not None:
        p.target_end_date = target_end_date
    if start_date is not None:
        p.start_date = start_date
    if program_id is not None:
        p.program_id = program_id
    if leader_id is not None:
        p.leader_id = leader_id
    # Sheet 1
    if product_type is not None:
        p.product_type = product_type
    if target_market is not None:
        p.target_market = target_market
    if climate_zone is not None:
        p.climate_zone = climate_zone
    if refrigerant is not None:
        p.refrigerant = refrigerant
    if capacity_range is not None:
        p.capacity_range = capacity_range
    if voltage_freq is not None:
        p.voltage_freq = voltage_freq
    if series_name is not None:
        p.series_name = series_name
    if energy_rating is not None:
        p.energy_rating = energy_rating
    if ip_ownership is not None:
        p.ip_ownership = ip_ownership
    if project_duration is not None:
        p.project_duration = project_duration
    if dev_category is not None:
        p.dev_category = dev_category
    if project_origin is not None:
        p.project_origin = project_origin
    if background_basis is not None:
        p.background_basis = background_basis
    if overall_goal is not None:
        p.overall_goal = overall_goal
    if tech_goal is not None:
        p.tech_goal = tech_goal
    if cost_goal is not None:
        p.cost_goal = cost_goal
    if sales_goal is not None:
        p.sales_goal = sales_goal
    if cert_goal is not None:
        p.cert_goal = cert_goal
    if schedule_goal is not None:
        p.schedule_goal = schedule_goal
    if patent_goal is not None:
        p.patent_goal = patent_goal
    if other_goals is not None:
        p.other_goals = other_goals
    if deliverables is not None:
        p.deliverables = deliverables
    if sample_qty is not None:
        p.sample_qty = sample_qty
    if required_date is not None:
        p.required_date = required_date
    # Sheet 2
    if main_capacity is not None:
        p.main_capacity = main_capacity
    if energy_efficiency_req is not None:
        p.energy_efficiency_req = energy_efficiency_req
    if cert_requirements is not None:
        p.cert_requirements = cert_requirements
    if target_price is not None:
        p.target_price = target_price
    if customer_requirements is not None:
        p.customer_requirements = customer_requirements
    # Sheet 3
    if core_performance is not None:
        p.core_performance = core_performance
    if safety_compliance is not None:
        p.safety_compliance = safety_compliance
    if optional_config is not None:
        p.optional_config = optional_config
    # Sheet 4
    if dev_cost_items is not None:
        p.dev_cost_items = dev_cost_items
    if economic_indicators is not None:
        p.economic_indicators = economic_indicators
    if mold_costs is not None:
        p.mold_costs = mold_costs
    if prototype_costs_detail is not None:
        p.prototype_costs_detail = prototype_costs_detail
    if test_costs is not None:
        p.test_costs = test_costs
    if labor_costs is not None:
        p.labor_costs = labor_costs
    # Sheet 5
    if customer_name is not None:
        p.customer_name = customer_name
    if other_requirements is not None:
        p.other_requirements = other_requirements
    if accessory_config is not None:
        p.accessory_config = accessory_config
    if feature_config is not None:
        p.feature_config = feature_config
    if fob_price is not None:
        p.fob_price = fob_price
    if bom_cost_target is not None:
        p.bom_cost_target = bom_cost_target
    if bom_cost_ratio is not None:
        p.bom_cost_ratio = bom_cost_ratio
    if manufacturing_cost is not None:
        p.manufacturing_cost = manufacturing_cost
    if gross_margin is not None:
        p.gross_margin = gross_margin
    if annual_sales_forecast is not None:
        p.annual_sales_forecast = annual_sales_forecast
    if product_lifecycle is not None:
        p.product_lifecycle = product_lifecycle
    if mold_inner is not None:
        p.mold_inner = mold_inner
    if mold_outer is not None:
        p.mold_outer = mold_outer
    # Sheet 5
    if team_members is not None:
        p.team_members = team_members


# ══════════════════════════════════════════════════════════════
# POST /api/pm/project — PM 一站式快捷创建项目
# ══════════════════════════════════════════════════════════════

@router.post("/project")
def pm_create_project(
    name: str = Body(..., max_length=200),
    description: str | None = Body(None),
    market_policy: str | None = Body(None, max_length=200),
    annual_planning_ref: str | None = Body(None, max_length=100),
    budget: int | None = Body(None),
    product_code: str | None = Body(None, max_length=50),
    project_class: str = Body("B", pattern="^(T|A|B|C)$"),
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
    # Sheet 5 - 团队与职责
    team_members: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """PM 快捷创建正式项目 — 自动以当前 PM 为 owner, 自动生成 code, is_draft=False"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    # 自动生成项目编号
    code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
    while db.query(Project).filter(Project.code == code, Project.is_deleted == False).first():
        code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"

    p = Project(
        code=code,
        name=name.strip(),
        project_class=project_class,
        source=source,
        target_end_date=target_end_date,
        owner=current_user.username,
        status="planning",
        is_draft=False,
        program_id=program_id,
        leader_id=leader_id,
    )
    # 应用所有可选字段
    _apply_project_fields(
        p,
        name=name,
        description=description,
        market_policy=market_policy,
        annual_planning_ref=annual_planning_ref,
        budget=budget,
        product_code=product_code,
        project_class=project_class,
        source=source,
        target_end_date=target_end_date,
        start_date=start_date,
        program_id=program_id,
        leader_id=leader_id,
        product_type=product_type,
        target_market=target_market,
        climate_zone=climate_zone,
        refrigerant=refrigerant,
        capacity_range=capacity_range,
        voltage_freq=voltage_freq,
        series_name=series_name,
        energy_rating=energy_rating,
        ip_ownership=ip_ownership,
        project_duration=project_duration,
        dev_category=dev_category,
        project_origin=project_origin,
        background_basis=background_basis,
        overall_goal=overall_goal,
        tech_goal=tech_goal,
        cost_goal=cost_goal,
        sales_goal=sales_goal,
        cert_goal=cert_goal,
        schedule_goal=schedule_goal,
        patent_goal=patent_goal,
        other_goals=other_goals,
        deliverables=deliverables,
        sample_qty=sample_qty,
        required_date=required_date,
        main_capacity=main_capacity,
        energy_efficiency_req=energy_efficiency_req,
        cert_requirements=cert_requirements,
        target_price=target_price,
        customer_requirements=customer_requirements,
        core_performance=core_performance,
        safety_compliance=safety_compliance,
        optional_config=optional_config,
        dev_cost_items=dev_cost_items,
        economic_indicators=economic_indicators,
        mold_costs=mold_costs,
        prototype_costs_detail=prototype_costs_detail,
        team_members=team_members,
    )

    # ── 自动计算：制冷量 BTU → 瓦特，注入 core_performance ──
    if capacity_range:
        p.core_performance = inject_cooling_capacity_to_core_performance(
            p.core_performance, capacity_range
        )
    # ── 自动计算：人月费用，写入 labor_costs ──
    if project_duration or team_members:
        p.labor_costs = generate_labor_costs_json(project_duration, team_members)

    try:
        db.add(p)
        db.flush()

        # 根据项目等级自动生成 Gate 模板
        from app.api.projects import _get_gate_template
        from app.models.project import ProjectGate
        template = _get_gate_template(project_class)
        for gate_def in template:
            db.add(ProjectGate(
                project_id=p.id,
                gate_code=gate_def["code"],
                gate_name=gate_def["name"],
                seq=gate_def["seq"],
                decision_level=gate_def["decision_level"],
                is_high_risk_zone=gate_def["is_high_risk_zone"],
                is_hidden=gate_def["is_hidden"],
            ))

        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise

    return _project_to_dict(p)


# ══════════════════════════════════════════════════════════════
# POST /api/pm/project/draft — 保存草稿项目
# ══════════════════════════════════════════════════════════════

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
    # Sheet 5 - 团队与职责
    team_members: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """PM 保存草稿项目 — is_draft=True, status='draft', 不生成 code 和 Gate 模板"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    p = Project(
        name=name.strip(),
        project_class=project_class,
        owner=current_user.username,
        status="draft",
        is_draft=True,
        program_id=program_id,
        leader_id=leader_id,
    )
    # 应用所有可选字段
    _apply_project_fields(
        p,
        name=name,
        description=description,
        market_policy=market_policy,
        annual_planning_ref=annual_planning_ref,
        budget=budget,
        product_code=product_code,
        project_class=project_class,
        source=source,
        target_end_date=target_end_date,
        start_date=start_date,
        program_id=program_id,
        leader_id=leader_id,
        product_type=product_type,
        target_market=target_market,
        climate_zone=climate_zone,
        refrigerant=refrigerant,
        capacity_range=capacity_range,
        voltage_freq=voltage_freq,
        series_name=series_name,
        energy_rating=energy_rating,
        ip_ownership=ip_ownership,
        project_duration=project_duration,
        dev_category=dev_category,
        project_origin=project_origin,
        background_basis=background_basis,
        overall_goal=overall_goal,
        tech_goal=tech_goal,
        cost_goal=cost_goal,
        sales_goal=sales_goal,
        cert_goal=cert_goal,
        schedule_goal=schedule_goal,
        patent_goal=patent_goal,
        other_goals=other_goals,
        deliverables=deliverables,
        sample_qty=sample_qty,
        required_date=required_date,
        main_capacity=main_capacity,
        energy_efficiency_req=energy_efficiency_req,
        cert_requirements=cert_requirements,
        target_price=target_price,
        customer_requirements=customer_requirements,
        core_performance=core_performance,
        safety_compliance=safety_compliance,
        optional_config=optional_config,
        dev_cost_items=dev_cost_items,
        economic_indicators=economic_indicators,
        mold_costs=mold_costs,
        prototype_costs_detail=prototype_costs_detail,
        team_members=team_members,
    )

    # ── 自动计算：制冷量 BTU → 瓦特，注入 core_performance ──
    if capacity_range:
        p.core_performance = inject_cooling_capacity_to_core_performance(
            p.core_performance, capacity_range
        )
    # ── 自动计算：人月费用，写入 labor_costs ──
    if project_duration or team_members:
        p.labor_costs = generate_labor_costs_json(project_duration, team_members)

    try:
        db.add(p)
        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise

    return _project_to_dict(p)


# ══════════════════════════════════════════════════════════════
# PUT /api/pm/project/draft/{pid} — 更新草稿项目
# ══════════════════════════════════════════════════════════════

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
    # Sheet 5 - 团队与职责
    team_members: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """PM 更新草稿项目 — 仅 owner 本人可编辑, 使用 is not None 判断"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证当前用户是项目 owner
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可更新此项目")

    try:
        # 使用 is not None 判断 (而非真值判断) 以支持清空字段
        _apply_project_fields(
            p,
            name=name,
            description=description,
            market_policy=market_policy,
            annual_planning_ref=annual_planning_ref,
            budget=budget,
            product_code=product_code,
            project_class=project_class,
            source=source,
            target_end_date=target_end_date,
            program_id=program_id,
            leader_id=leader_id,
            product_type=product_type,
            target_market=target_market,
            climate_zone=climate_zone,
            refrigerant=refrigerant,
            capacity_range=capacity_range,
            voltage_freq=voltage_freq,
            series_name=series_name,
            energy_rating=energy_rating,
            ip_ownership=ip_ownership,
            project_duration=project_duration,
            dev_category=dev_category,
            project_origin=project_origin,
            background_basis=background_basis,
            overall_goal=overall_goal,
            tech_goal=tech_goal,
            cost_goal=cost_goal,
            sales_goal=sales_goal,
            cert_goal=cert_goal,
            schedule_goal=schedule_goal,
            patent_goal=patent_goal,
            other_goals=other_goals,
            deliverables=deliverables,
            sample_qty=sample_qty,
            required_date=required_date,
            main_capacity=main_capacity,
            energy_efficiency_req=energy_efficiency_req,
            cert_requirements=cert_requirements,
            target_price=target_price,
            customer_requirements=customer_requirements,
            core_performance=core_performance,
            safety_compliance=safety_compliance,
            optional_config=optional_config,
            dev_cost_items=dev_cost_items,
            economic_indicators=economic_indicators,
            mold_costs=mold_costs,
            prototype_costs_detail=prototype_costs_detail,
            team_members=team_members,
        )

        # ── 自动计算：制冷量 BTU → 瓦特 ──
        if capacity_range and p.capacity_range:
            p.core_performance = inject_cooling_capacity_to_core_performance(
                p.core_performance, p.capacity_range
            )
        # ── 自动计算：人月费用 ──
        if project_duration is not None or team_members is not None:
            from app.api.pm_proposal_utils import generate_labor_costs_json as _gen_labor
            p.labor_costs = _gen_labor(
                project_duration if project_duration is not None else p.project_duration,
                team_members if team_members is not None else p.team_members,
            )

        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise

    return _project_to_dict(p)


# ══════════════════════════════════════════════════════════════
# POST /api/pm/project/submit/{pid} — 草稿提交为正式项目
# ══════════════════════════════════════════════════════════════

@router.post("/project/submit/{pid}")
def pm_submit_draft(
    pid: int,
    start_date: date | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """草稿提交为正式项目 — is_draft=False, status='planning', 自动生成 code 和 Gate 模板"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证当前用户是项目 owner
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可提交此项目")

    # 验证是否为草稿
    if not p.is_draft:
        raise HTTPException(status_code=400, detail="该项目已提交，无法重复提交")

    try:
        # 自动生成项目编号 (如果还没有)
        if not p.code:
            code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
            while db.query(Project).filter(Project.code == code, Project.is_deleted == False).first():
                code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
            p.code = code

        # 转为正式项目
        p.is_draft = False
        p.status = "planning"

        # ── 提交时自动生成认证费用（写入 cert_costs）──
        if p.safety_compliance:
            cert_rows = get_cert_costs_from_compliance(p.safety_compliance)
            p.cert_costs = json.dumps(cert_rows, ensure_ascii=False, default=str)
        # ── 提交时自动计算人月费用（写入 labor_costs）──
        if p.project_duration or p.team_members:
            p.labor_costs = generate_labor_costs_json(p.project_duration, p.team_members)
        # ── 提交时自动计算制冷量 ──
        if p.capacity_range:
            p.core_performance = inject_cooling_capacity_to_core_performance(
                p.core_performance, p.capacity_range
            )

        db.flush()

        # 自动生成 Gate 模板 (如果还没有)
        from app.api.projects import _get_gate_template
        from app.models.project import ProjectGate
        existing_gates = db.query(ProjectGate).filter(
            ProjectGate.project_id == pid
        ).count()
        if existing_gates == 0:
            project_class = p.project_class or "B"
            template = _get_gate_template(project_class)
            for gate_def in template:
                db.add(ProjectGate(
                    project_id=p.id,
                    gate_code=gate_def["code"],
                    gate_name=gate_def["name"],
                    seq=gate_def["seq"],
                    decision_level=gate_def["decision_level"],
                    is_high_risk_zone=gate_def["is_high_risk_zone"],
                    is_hidden=gate_def["is_hidden"],
                ))

        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise

    return _project_to_dict(p)


# ══════════════════════════════════════════════════════════════
# PATCH /api/pm/project/{pid} — PM 快捷更新项目
# ══════════════════════════════════════════════════════════════

@router.patch("/project/{pid}")
def pm_update_project(
    pid: int,
    description: str | None = Body(None),
    market_policy: str | None = Body(None, max_length=200),
    annual_planning_ref: str | None = Body(None, max_length=100),
    budget: int | None = Body(None),
    target_end_date: date | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """PM 快捷更新项目 — 仅 owner 本人可编辑"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证当前用户是项目 owner
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可更新此项目")

    try:
        if description is not None:
            p.description = description
        if market_policy is not None:
            p.market_policy = market_policy
        if annual_planning_ref is not None:
            p.annual_planning_ref = annual_planning_ref
        if budget is not None:
            p.budget = budget
        if target_end_date is not None:
            p.target_end_date = target_end_date

        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise

    return _project_to_dict(p)
