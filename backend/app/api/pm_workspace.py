"""产品经理(PM)工作台API — 聚合视图 + 快捷CRUD + Product Initiation Draft 管理

提供 PM 角色专属的项目管理工作台:
- GET  /api/pm/workspace          — 聚合面板数据
- GET  /api/pm/proposals          — 我的提案列表
- POST /api/pm/project/draft      — 保存草稿项目
- PUT  /api/pm/project/draft/{pid} — 更新草稿项目
- POST /api/pm/proposals/submit   — 提交立项审批
- POST /api/pm/proposals/{id}/withdraw — 撤回立项审批
"""
from datetime import datetime, date
import json
import random
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.system_config import SystemConfig
from app.models.user import User
from app.models.project import Project, Program
from app.models.product import Product, Platform
from app.models.annual_plan import AnnualPlan
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.product_plan_subs import ProductPlanInitiation, ProductPlanMarket, ProductPlanTechSpec, ProductPlanTeam
from app.core.security import require_role
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
    """将 Project ORM 对象转为包含所有 Initiation 字段的 dict
    
    当项目有关联 ProductPlan 时，从子表读取 Sheet1-5 字段；
    无关联时返回空值（向后兼容）。
    """
    # 从 ProductPlan 子表解析字段
    init = None
    market = None
    tech = None
    team_list = None
    if p.product_plan_id:
        plan = p.product_plan
        if plan:
            init = plan.initiation
            market = plan.market_info
            tech = plan.tech_spec
            team_list = plan.team_members

    def _v(obj, attr, default=None):
        """Safe attribute access"""
        return getattr(obj, attr, default) if obj else default

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
        # Sheet 1 - 项目概述 (from ProductPlanInitiation)
        "product_type": _v(init, "product_type"),
        "target_market": _v(init, "target_market"),
        "climate_zone": _v(init, "climate_zone"),
        "refrigerant": _v(init, "refrigerant"),
        "capacity_range": _v(init, "capacity_range"),
        "voltage_freq": _v(init, "voltage_freq"),
        "series_name": _v(init, "series_name"),
        "energy_rating": _v(init, "energy_rating"),
        "ip_ownership": _v(init, "ip_ownership"),
        "project_duration": _v(init, "project_duration"),
        "dev_category": _v(init, "dev_category"),
        "project_origin": _v(init, "project_origin"),
        "background_basis": _v(init, "background_basis"),
        "overall_goal": _v(init, "overall_goal"),
        "tech_goal": _v(init, "tech_goal"),
        "cost_goal": _v(init, "cost_goal"),
        "sales_goal": _v(init, "sales_goal"),
        "cert_goal": _v(init, "cert_goal"),
        "schedule_goal": _v(init, "schedule_goal"),
        "patent_goal": _v(init, "patent_goal"),
        "other_goals": _v(init, "other_goals"),
        "deliverables": _v(init, "deliverables"),
        "sample_qty": _v(init, "sample_qty"),
        "required_date": str(_v(init, "required_date")) if _v(init, "required_date") else None,
        # Sheet 2 - 市场与客户需求 (from ProductPlanMarket)
        "main_capacity": _v(market, "main_capacity"),
        "energy_efficiency_req": _v(market, "energy_efficiency_req"),
        "cert_requirements": _v(market, "cert_requirements"),
        "target_price": _v(market, "target_price"),
        "customer_requirements": _v(market, "customer_requirements"),
        # Sheet 3 - 技术要求 (from ProductPlanTechSpec)
        "core_performance": _v(tech, "core_performance"),
        "safety_compliance": _v(tech, "safety_compliance"),
        "optional_config": _v(tech, "optional_config"),
        # Sheet 4 - 成本核算 (from ProductPlanInitiation)
        "dev_cost_items": _v(init, "dev_cost_items"),
        "economic_indicators": _v(init, "economic_indicators"),
        "mold_costs": _v(init, "mold_costs"),
        "prototype_costs_detail": _v(init, "prototype_costs_detail"),
        "test_costs": _v(init, "test_costs"),
        "cert_costs": _v(init, "cert_costs"),
        "labor_costs": _v(init, "labor_costs"),
        # Sheet 5 - 团队 (from ProductPlanTeam 1:N)
        "team_members": json.dumps([{
            "role_name": t.role_name,
            "member_name": t.member_name,
            "department": t.department,
            "responsibility": t.responsibility,
        } for t in (team_list or [])], ensure_ascii=False) if team_list else None,
        # New fields (Excel alignment) — from ProductPlanInitiation
        "customer_name": _v(init, "customer_name"),
        "other_requirements": _v(init, "other_requirements"),
        "accessory_config": _v(init, "accessory_config"),
        "feature_config": _v(init, "feature_config"),
        "fob_price": _v(init, "fob_price"),
        "bom_cost_target": _v(init, "bom_cost_target"),
        "bom_cost_ratio": _v(init, "bom_cost_ratio"),
        "manufacturing_cost": _v(init, "manufacturing_cost"),
        "gross_margin": _v(init, "gross_margin"),
        "annual_sales_forecast": _v(init, "annual_sales_forecast"),
        "product_lifecycle": _v(init, "product_lifecycle"),
        "mold_inner": _v(init, "mold_inner"),
        "mold_outer": _v(init, "mold_outer"),
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

    # ── 年度规划列表（从AnnualPlan表查询，附加project_count）──
    annual_plans_raw = db.query(AnnualPlan).order_by(AnnualPlan.year.desc(), AnnualPlan.created_at.desc()).all()
    planning_items = []
    for ap in annual_plans_raw:
        project_count = 0  # TODO: 等Project模型同步后恢复真实计数
        planning_items.append({
            "id": ap.id,
            "name": ap.name,
            "year": ap.year,
            "description": ap.description,
            "doc_ref": ap.doc_ref,
            "owner": ap.owner,
            "project_count": project_count,
            "created_at": str(ap.created_at) if ap.created_at else None,
            "updated_at": str(ap.updated_at) if ap.updated_at else None,
        })

    # ── 最近5个项目 ──
    recent_projects = my_projects[:5] if len(my_projects) > 5 else my_projects

    return {
        "my_projects": my_projects,
        "products": products,
        "stats": stats,
        "planning_items": planning_items,
        "recent_projects": recent_projects,
    }


# ══════════════════════════════════════════════════════════════
# GET /api/pm/proposals — 我的提案列表
# ══════════════════════════════════════════════════════════════

@router.get("/proposals")
def list_my_proposals(
    status: str = Query("all", description="过滤状态: draft(草稿) / submitted(已提交) / all(全部)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """返回当前用户的所有提案（含草稿和已提交）
    
    - 查询 projects 表: owner=current_user, is_deleted=False
    - status 参数:
        - draft: 仅返回 is_draft=True
        - submitted: 仅返回 is_draft=False
        - all(默认): 返回全部
    - 返回格式与 my_projects 一致
    """
    owner_name = current_user.username

    query = db.query(Project).filter(
        Project.owner == owner_name,
        Project.is_deleted == False,
    )

    if status == "draft":
        query = query.filter(Project.is_draft == True)
    elif status == "submitted":
        query = query.filter(Project.is_draft == False)
    # "all" — no additional filter

    proposals_raw = query.order_by(Project.updated_at.desc()).all()

    proposals = [_project_to_dict(p) for p in proposals_raw]

    return {
        "proposals": proposals,
        "total": len(proposals),
        "draft_count": sum(1 for p in proposals_raw if p.is_draft),
        "submitted_count": sum(1 for p in proposals_raw if not p.is_draft),
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
    cert_costs: str | None = None,
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
    """将非 None 参数写入 Project 对象（基础字段直接写，Sheet1-5 写 ProductPlan 子表）"""
    # ---- 基础 Project 字段 ----
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

    # ---- Sheet1-5 字段写入 ProductPlan 子表 ----
    plan = p.product_plan if p.product_plan_id else None
    if plan is None:
        # 无关联 ProductPlan，直接跳过（不报错，向后兼容）
        return

    # 确保子表记录存在
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
    if product_type is not None:
        init.product_type = product_type
    if target_market is not None:
        init.target_market = target_market
    if climate_zone is not None:
        init.climate_zone = climate_zone
    if refrigerant is not None:
        init.refrigerant = refrigerant
    if capacity_range is not None:
        init.capacity_range = capacity_range
    if voltage_freq is not None:
        init.voltage_freq = voltage_freq
    if series_name is not None:
        init.series_name = series_name
    if energy_rating is not None:
        init.energy_rating = energy_rating
    if ip_ownership is not None:
        init.ip_ownership = ip_ownership
    if project_duration is not None:
        init.project_duration = project_duration
    if dev_category is not None:
        init.dev_category = dev_category
    if project_origin is not None:
        init.project_origin = project_origin
    if background_basis is not None:
        init.background_basis = background_basis
    if overall_goal is not None:
        init.overall_goal = overall_goal
    if tech_goal is not None:
        init.tech_goal = tech_goal
    if cost_goal is not None:
        init.cost_goal = cost_goal
    if sales_goal is not None:
        init.sales_goal = sales_goal
    if cert_goal is not None:
        init.cert_goal = cert_goal
    if schedule_goal is not None:
        init.schedule_goal = schedule_goal
    if patent_goal is not None:
        init.patent_goal = patent_goal
    if other_goals is not None:
        init.other_goals = other_goals
    if deliverables is not None:
        init.deliverables = deliverables
    if sample_qty is not None:
        init.sample_qty = sample_qty
    if required_date is not None:
        init.required_date = required_date

    # Sheet 2 → ProductPlanMarket
    if main_capacity is not None:
        market.main_capacity = main_capacity
    if energy_efficiency_req is not None:
        market.energy_efficiency_req = energy_efficiency_req
    if cert_requirements is not None:
        market.cert_requirements = cert_requirements
    if target_price is not None:
        market.target_price = target_price
    if customer_requirements is not None:
        market.customer_requirements = customer_requirements

    # Sheet 3 → ProductPlanTechSpec
    if core_performance is not None:
        tech.core_performance = core_performance
    if safety_compliance is not None:
        tech.safety_compliance = safety_compliance
    if optional_config is not None:
        tech.optional_config = optional_config

    # Sheet 4 (costs) → ProductPlanInitiation
    if dev_cost_items is not None:
        init.dev_cost_items = dev_cost_items
    if economic_indicators is not None:
        init.economic_indicators = economic_indicators
    if mold_costs is not None:
        init.mold_costs = mold_costs
    if prototype_costs_detail is not None:
        init.prototype_costs_detail = prototype_costs_detail
    if test_costs is not None:
        init.test_costs = test_costs
    if cert_costs is not None:
        init.cert_costs = cert_costs
    if labor_costs is not None:
        init.labor_costs = labor_costs

    # New fields → ProductPlanInitiation
    if customer_name is not None:
        init.customer_name = customer_name
    if other_requirements is not None:
        init.other_requirements = other_requirements
    if accessory_config is not None:
        init.accessory_config = accessory_config
    if feature_config is not None:
        init.feature_config = feature_config
    if fob_price is not None:
        init.fob_price = fob_price
    if bom_cost_target is not None:
        init.bom_cost_target = bom_cost_target
    if bom_cost_ratio is not None:
        init.bom_cost_ratio = bom_cost_ratio
    if manufacturing_cost is not None:
        init.manufacturing_cost = manufacturing_cost
    if gross_margin is not None:
        init.gross_margin = gross_margin
    if annual_sales_forecast is not None:
        init.annual_sales_forecast = annual_sales_forecast
    if product_lifecycle is not None:
        init.product_lifecycle = product_lifecycle
    if mold_inner is not None:
        init.mold_inner = mold_inner
    if mold_outer is not None:
        init.mold_outer = mold_outer

    # Sheet 5 (team) → ProductPlanTeam (1:N, 替换策略)
    if team_members is not None:
        # 清除旧的团队成员
        for old_t in list(plan.team_members):
            plan.team_members.remove(old_t)
        # 解析 JSON 并创建新成员
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
            pass  # 静默忽略解析失败





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
    db.add(p)
    db.flush()

    # ── 创建 ProductPlan（DRAFT）+ 子表记录 ──
    plan = ProductPlan(
        name=p.name,
        status=ProductPlanStage.DRAFT,
        created_by=current_user.username,
    )
    db.add(plan)
    db.flush()
    p.product_plan_id = plan.id

    # 创建子表空记录
    init = ProductPlanInitiation(product_plan_id=plan.id)
    market = ProductPlanMarket(product_plan_id=plan.id)
    tech = ProductPlanTechSpec(product_plan_id=plan.id)
    db.add(init)
    db.add(market)
    db.add(tech)

    # 应用所有可选字段（现在会写入 ProductPlan 子表）
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
        customer_name=customer_name,
        other_requirements=other_requirements,
        accessory_config=accessory_config,
        feature_config=feature_config,
        fob_price=fob_price,
        bom_cost_target=bom_cost_target,
        bom_cost_ratio=bom_cost_ratio,
        manufacturing_cost=manufacturing_cost,
        gross_margin=gross_margin,
        annual_sales_forecast=annual_sales_forecast,
        product_lifecycle=product_lifecycle,
        mold_inner=mold_inner,
        mold_outer=mold_outer,
    )

    # ── 自动计算：制冷量 BTU → 瓦特，注入 core_performance ──
    if capacity_range and plan.tech_spec:
        plan.tech_spec.core_performance = inject_cooling_capacity_to_core_performance(
            plan.tech_spec.core_performance, capacity_range
        )
    # ── 自动计算：人月费用，写入 labor_costs ──
    if project_duration or team_members:
        plan.initiation.labor_costs = generate_labor_costs_json(project_duration, team_members)

    try:
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
):
    """PM 更新草稿项目 — 仅 owner 本人可编辑, 使用 is not None 判断"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证当前用户是项目 owner
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可更新此项目")

    # 只有草稿状态的项目才能编辑（防覆盖已提交的项目）
    if not p.is_draft:
        raise HTTPException(status_code=400, detail="已提交或审批中的项目不可编辑，如需修改请撤回审批")

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
            test_costs=test_costs,
            cert_costs=cert_costs,
            team_members=team_members,
            customer_name=customer_name,
            other_requirements=other_requirements,
            accessory_config=accessory_config,
            feature_config=feature_config,
            fob_price=fob_price,
            bom_cost_target=bom_cost_target,
            bom_cost_ratio=bom_cost_ratio,
            manufacturing_cost=manufacturing_cost,
            gross_margin=gross_margin,
            annual_sales_forecast=annual_sales_forecast,
            product_lifecycle=product_lifecycle,
            mold_inner=mold_inner,
            mold_outer=mold_outer,
        )

        # ── 自动计算：制冷量 BTU → 瓦特 ──
        if capacity_range and p.product_plan and p.product_plan.tech_spec:
            plan_tech = p.product_plan.tech_spec
            plan_tech.core_performance = inject_cooling_capacity_to_core_performance(
                plan_tech.core_performance, capacity_range
            )
        # ── 自动计算：人月费用 ──
        if project_duration is not None or team_members is not None:
            from app.api.pm_proposal_utils import generate_labor_costs_json as _gen_labor
            if p.product_plan and p.product_plan.initiation:
                plan_init = p.product_plan.initiation
                plan_init.labor_costs = _gen_labor(
                    project_duration if project_duration is not None else plan_init.project_duration,
                    team_members if team_members is not None else None,
                )

        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise

    return _project_to_dict(p)





# ══════════════════════════════════════════════════════════════
# 年度规划 (AnnualPlan) CRUD — P2.1 ~ P2.3
# ══════════════════════════════════════════════════════════════

def _planning_item_to_dict(ap: AnnualPlan, project_count: int = 0) -> dict:
    """将 AnnualPlan ORM 对象转为包含 project_count 的 dict"""
    return {
        "id": ap.id,
        "name": ap.name,
        "year": ap.year,
        "description": ap.description,
        "doc_ref": ap.doc_ref,
        "owner": ap.owner,
        "project_count": project_count,
        "created_at": str(ap.created_at) if ap.created_at else None,
        "updated_at": str(ap.updated_at) if ap.updated_at else None,
    }


@router.get("/planning-items")
def list_planning_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
):
    """获取年度规划列表，附加每个规划关联的项目数"""
    plans = db.query(AnnualPlan).order_by(AnnualPlan.year.desc(), AnnualPlan.created_at.desc()).all()
    result = []
    for ap in plans:
        project_count = 0  # TODO: 等Project模型同步后恢复真实计数
        result.append(_planning_item_to_dict(ap, project_count))
    return result


@router.post("/planning-items")
def create_planning_item(
    name: str = Body(..., max_length=200),
    year: int = Body(...),
    description: str | None = Body(None),
    doc_ref: str | None = Body(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
):
    """创建年度规划条目"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="规划名称不能为空")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="请输入有效的年度")

    # 检查同一年度下是否已有同名规划
    existing = db.query(AnnualPlan).filter(
        AnnualPlan.name == name.strip(),
        AnnualPlan.year == year,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"年度 {year} 下已存在同名规划 '{name}'")

    ap = AnnualPlan(
        name=name.strip(),
        year=year,
        description=description,
        doc_ref=doc_ref,
        owner=current_user.username,
    )
    try:
        db.add(ap)
        db.commit()
        db.refresh(ap)
    except Exception:
        db.rollback()
        raise

    return _planning_item_to_dict(ap, 0)


@router.put("/planning-items/{plan_id}")
def update_planning_item(
    plan_id: int,
    name: str | None = Body(None, max_length=200),
    year: int | None = Body(None),
    description: str | None = Body(None),
    doc_ref: str | None = Body(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
):
    """更新年度规划条目"""
    ap = db.query(AnnualPlan).filter(AnnualPlan.id == plan_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="年度规划不存在")
    
    # 所有权校验
    if ap.owner != current_user.username:
        raise HTTPException(status_code=403, detail="无权修改他人的年度规划")

    try:
        if name is not None:
            if not name.strip():
                raise HTTPException(status_code=400, detail="规划名称不能为空")
            ap.name = name.strip()
        if year is not None:
            if year < 2000 or year > 2100:
                raise HTTPException(status_code=400, detail="请输入有效的年度")
            ap.year = year
        if description is not None:
            ap.description = description
        if doc_ref is not None:
            ap.doc_ref = doc_ref

        db.commit()
        db.refresh(ap)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    # 返回时附加 project_count (TODO: 等Project模型同步后恢复)
    project_count = 0
    return _planning_item_to_dict(ap, project_count)


@router.delete("/planning-items/{plan_id}")
def delete_planning_item(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
):
    """删除年度规划条目"""
    ap = db.query(AnnualPlan).filter(AnnualPlan.id == plan_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="年度规划不存在")
    
    # 所有权校验
    if ap.owner != current_user.username:
        raise HTTPException(status_code=403, detail="无权删除他人的年度规划")
    
    # 检查关联项目
    if db.query(Project).filter(Project.annual_planning_ref == ap.name, Project.is_deleted == False).count() > 0:
        raise HTTPException(status_code=409, detail="该规划下存在关联项目，请先解除关联后再删除")

    try:
        db.delete(ap)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"detail": "年度规划已删除"}


# ══════════════════════════════════════════════════════════════
# GET /api/pm/capacity-cost-config — 冷量段成本配置查询
# ══════════════════════════════════════════════════════════════

def _normalize_capacity_key(capacity_range: str) -> str:
    """Normalize capacity range key: '7K' → '07K', '12K' → '12K'"""
    cap = capacity_range.strip().upper()
    if len(cap) == 2 and cap[0].isdigit() and cap[1] == 'K':
        return '0' + cap
    return cap


def _extract_capacity_number(capacity_range: str) -> int:
    """Extract numeric part from capacity range: '12K' → 12, '07K' → 7"""
    cap = capacity_range.strip().upper().rstrip('K')
    try:
        return int(cap)
    except ValueError:
        return 0


@router.get("/capacity-cost-config")
def get_capacity_cost_config(
    capacity_range: str = Query(..., description="冷量段，如 12K, 07K, 18K"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """返回该冷量段对应的完整成本配置。
    
    从 system_config 表读取 mfg_cost_threshold, capacity_unit_cost_map, 
    test_unit_price, indirect_cost，合并计算后返回。
    """
    # 读取所有需要的配置
    config_keys = ["mfg_cost_threshold", "capacity_unit_cost_map", "test_unit_price", "indirect_cost"]
    rows = db.query(SystemConfig).filter(SystemConfig.key.in_(config_keys)).all()
    config = {row.key: row.value for row in rows}
    
    # ── 计算 manufacturing_cost ──
    manufacturing_cost = 0
    cap_num = _extract_capacity_number(capacity_range)
    if "mfg_cost_threshold" in config:
        try:
            thresholds = json.loads(config["mfg_cost_threshold"])
            for t in thresholds:
                if cap_num <= t.get("max_kw", 0):
                    manufacturing_cost = t.get("cost", 0)
                    break
        except (json.JSONDecodeError, TypeError) as e:
            logging.getLogger(__name__).warning(f"mfg_cost_threshold JSON解析失败: {e}")
    
    # ── 计算 proto_unit_cost ──
    proto_unit_cost = 0.0
    if "capacity_unit_cost_map" in config:
        try:
            cost_map = json.loads(config["capacity_unit_cost_map"])
            normalized_key = _normalize_capacity_key(capacity_range)
            entry = cost_map.get(normalized_key)
            if entry and isinstance(entry, dict):
                proto_unit_cost = entry.get("cost", 0.0)
        except (json.JSONDecodeError, TypeError) as e:
            logging.getLogger(__name__).warning(f"capacity_unit_cost_map JSON解析失败: {e}")
    
    # ── test_unit_price ──
    try:
        test_unit_price = float(config.get("test_unit_price", "0"))
    except (ValueError, TypeError):
        test_unit_price = 0.0
    
    # ── indirect_cost ──
    try:
        indirect_cost = int(float(config.get("indirect_cost", "0")))
    except (ValueError, TypeError):
        indirect_cost = 0
    
    return {
        "manufacturing_cost": manufacturing_cost,
        "proto_unit_cost": proto_unit_cost,
        "test_unit_price": test_unit_price,
        "indirect_cost": indirect_cost,
    }


# ══════════════════════════════════════════════════════════════
# POST /api/pm/proposals/submit — 提交立项审批
# ══════════════════════════════════════════════════════════════


@router.post("/proposals/submit")
def submit_proposal(
    project_id: int = Body(..., description="项目ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """提交项目立项 — 推进关联 ProductPlan 到 PROJECT_INIT 并创建审批请求"""
    # 查找项目
    p = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 验证当前用户是项目 owner
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可提交立项")

    # 查找关联 ProductPlan
    plan_id = p.product_plan_id
    if not plan_id:
        raise HTTPException(status_code=400, detail="项目未关联产品策划，无法提交审批")

    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="关联的产品策划不存在")

    from app.services.product_plan_workflow import advance_stage

    # 将 ProductPlan 逐步推进到 PROJECT_INIT
    stage_order = [
        ProductPlanStage.DRAFT,
        ProductPlanStage.COMPETITOR,
        ProductPlanStage.DEFINITION,
        ProductPlanStage.COSTING,
        ProductPlanStage.TECH_INPUT,
        ProductPlanStage.PROJECT_INIT,
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
            raise HTTPException(
                status_code=400,
                detail=f"产品策划已超出立项阶段（当前: {ProductPlanStage.PROJECT_INIT.value}），无法重复提交",
            )

    # 创建审批请求
    from app.services.product_plan_approval import create_plan_approval
    approval = create_plan_approval(plan_id, db, current_user.username)

    return {
        "plan_id": plan_id,
        "plan_status": plan.status.value,
        "approval_id": approval.id,
        "message": "项目已提交审批",
    }


# ══════════════════════════════════════════════════════════════
# POST /api/pm/proposals/{proposal_id}/withdraw — 撤回立项审批
# ══════════════════════════════════════════════════════════════


@router.post("/proposals/{proposal_id}/withdraw")
def withdraw_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
):
    """撤回立项审批请求 — 仅申请人可撤回，撤回后回退 ProductPlan 阶段"""
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == proposal_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="审批请求不存在")

    # 仅申请人可撤回
    if req.requester != current_user.username:
        raise HTTPException(status_code=403, detail="仅申请人可撤回审批")

    # 仅待审批状态可撤回
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"当前审批状态为「{req.status}」，无法撤回")

    # 更新审批状态
    req.status = "withdrawn"

    # 如果是产品策划审批，回退 ProductPlan 到 TECH_INPUT 阶段
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

    return {
        "id": req.id,
        "status": req.status,
        "message": "审批已撤回",
    }
