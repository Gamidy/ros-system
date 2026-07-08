"""
市场数据聚合服务

为AI辅助策划提供结构化的市场上下文信息，聚合以下数据维度：
1. 竞品信息  — competitor_models 表
2. 能效标准  — required_standards 表（按目标市场关联）
3. 历史策划  — product_plans + product_plan_markets 表
4. 成本基准  — costs 表（按 product_plan 关联）
5. 目标市场要求 — target_markets + required_tests + required_certifications
6. 补充字段  — 管理员手动录入的市场分析文本
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.target_market import (
    TargetMarket,
    RequiredTest,
    RequiredCertification,
    RequiredStandard,
)
from app.models.competitor import CompetitorModel
from app.models.product_plan import ProductPlan, Cost, ProductPlanStage
from app.models.product_plan_subs import ProductPlanMarket


def _query_competitors(market_code: str, db: Session) -> List[Dict[str, Any]]:
    """查询指定市场的竞品信息"""
    rows = (
        db.query(CompetitorModel)
        .filter(CompetitorModel.market == market_code)
        .order_by(CompetitorModel.brand, CompetitorModel.model)
        .all()
    )
    result = []
    for c in rows:
        result.append(
            {
                "id": c.id,
                "brand": c.brand,
                "model": c.model,
                "product_type": c.product_type,
                "cooling_capacity": c.cooling_capacity,
                "cooling_capacity_w": c.cooling_capacity_w,
                "heating_capacity_w": c.heating_capacity_w,
                "energy_rating": c.energy_rating,
                "cooling_w": c.cooling_w,
                "heating_w": c.heating_w,
                "eer": c.eer,
                "cspf": c.cspf,
                "noise_indoor_db": c.noise_indoor_db,
                "noise_outdoor_db": c.noise_outdoor_db,
                "airflow_m3h": c.airflow_m3h,
                "factory_price": c.factory_price,
                "launch_year": c.launch_year,
                "notes": c.notes,
            }
        )
    return result


def _query_energy_standards(market_id: int, db: Session) -> List[Dict[str, Any]]:
    """查询指定市场的能效标准"""
    rows = (
        db.query(RequiredStandard)
        .filter(RequiredStandard.target_market_id == market_id)
        .order_by(RequiredStandard.sort_order)
        .all()
    )
    return [
        {
            "id": s.id,
            "standard_code": s.standard_code,
            "standard_name": s.standard_name,
            "is_core": s.is_core,
        }
        for s in rows
    ]


def _query_market_requirements(market_id: int, db: Session) -> Dict[str, Any]:
    """查询目标市场的测试和认证要求"""
    tests = (
        db.query(RequiredTest)
        .filter(RequiredTest.target_market_id == market_id)
        .order_by(RequiredTest.sort_order)
        .all()
    )
    certs = (
        db.query(RequiredCertification)
        .filter(RequiredCertification.target_market_id == market_id)
        .order_by(RequiredCertification.sort_order)
        .all()
    )
    return {
        "required_tests": [
            {
                "id": t.id,
                "test_category": t.test_category,
                "standard": t.standard,
                "is_required": t.is_required,
            }
            for t in tests
        ],
        "required_certifications": [
            {
                "id": c.id,
                "cert_type": c.cert_type,
                "cert_body": c.cert_body,
                "is_mandatory": c.is_mandatory,
            }
            for c in certs
        ],
    }


def _query_historical_plans(market_code: str, db: Session) -> List[Dict[str, Any]]:
    """查询该市场下的历史产品策划记录（已通过审批或更高阶段的）"""
    rows = (
        db.query(ProductPlan)
        .filter(ProductPlan.market == market_code)
        .filter(ProductPlan.status.in_([ProductPlanStage.APPROVED, ProductPlanStage.RELEASED]))
        .order_by(ProductPlan.updated_at.desc())
        .limit(20)
        .all()
    )
    # Load market_info for each plan separately
    plan_ids = [p.id for p in rows]
    market_infos = {}
    if plan_ids:
        market_infos = {
            mi.product_plan_id: mi
            for mi in db.query(ProductPlanMarket)
            .filter(ProductPlanMarket.product_plan_id.in_(plan_ids))
            .all()
        }
    result = []
    for p in rows:
        item: Dict[str, Any] = {
            "id": p.id,
            "name": p.name,
            "series": p.series,
            "product_type": p.initiation.product_type if p.initiation else None,
            "capacity_range": p.initiation.capacity_range if p.initiation else None,
            "energy_rating": p.initiation.energy_rating if p.initiation else None,
            "refrigerant": p.initiation.refrigerant if p.initiation else None,
            "voltage_freq": p.initiation.voltage_freq if p.initiation else None,
            "target_market_detail": p.target_market_detail,
            "status": p.status.value if p.status else None,
            "created_at": str(p.created_at) if p.created_at else None,
        }
        if p.id in market_infos:
            mi = market_infos[p.id]
            item["market_info"] = {
                "main_capacity": mi.main_capacity,
                "energy_efficiency_req": mi.energy_efficiency_req,
                "cert_requirements": mi.cert_requirements,
                "target_price": mi.target_price,
                "customer_requirements": mi.customer_requirements,
            }
        result.append(item)
    return result


def _query_cost_benchmarks(market_code: str, db: Session) -> List[Dict[str, Any]]:
    """查询关联该市场的产品策划成本基准"""
    plan_ids = [
        r[0]
        for r in db.query(ProductPlan.id)
        .filter(ProductPlan.market == market_code)
        .filter(ProductPlan.status.in_([ProductPlanStage.APPROVED, ProductPlanStage.RELEASED]))
        .all()
    ]
    if not plan_ids:
        return []
    rows = (
        db.query(Cost)
        .filter(Cost.product_plan_id.in_(plan_ids))
        .order_by(Cost.product_plan_id, Cost.item_name)
        .all()
    )
    return [
        {
            "id": c.id,
            "product_plan_id": c.product_plan_id,
            "cost_type": c.cost_type.value if c.cost_type else None,
            "item_name": c.item_name,
            "target_value": c.target_value,
            "actual_value": c.actual_value,
            "currency": c.currency,
            "remark": c.remark,
        }
        for c in rows
    ]


def aggregate_market_context(
    market_id: int,
    db: Optional[Session] = None,
    supplementary_analysis: Optional[str] = None,
) -> Dict[str, Any]:
    """
    聚合指定市场的完整上下文数据，供AI辅助策划使用。

    Parameters
    ----------
    market_id : int
        target_markets 表的主键 ID
    db : Session, optional
        SQLAlchemy 数据库会话。未提供时自动创建新会话。
    supplementary_analysis : str, optional
        管理员手动补充的市场分析文本，会原样放入返回结果的
        "supplementary" 字段。

    Returns
    -------
    dict
        结构化 JSON，包含以下顶层键：
        - market_info         — 市场基本信息
        - energy_standards    — 能效标准列表
        - market_requirements — 测试与认证要求
        - competitors         — 竞品列表
        - historical_plans    — 历史策划记录
        - cost_benchmarks     — 成本基准数据
        - supplementary       — 管理员补充分析文本（可选）
    """
    if db is None:
        db = SessionLocal()
        own_session = True
    else:
        own_session = False

    try:
        # --- 1. 市场基本信息 ---
        market = (
            db.query(TargetMarket)
            .filter(TargetMarket.id == market_id)
            .first()
        )
        if not market:
            return {"error": f"Market with id={market_id} not found", "market_id": market_id}

        market_code = market.market_code
        market_info = {
            "id": market.id,
            "market_code": market.market_code,
            "market_name": market.market_name,
            "description": market.description,
        }

        # --- 2. 能效标准 ---
        energy_standards = _query_energy_standards(market_id, db)

        # --- 3. 市场要求（测试+认证）---
        market_requirements = _query_market_requirements(market_id, db)

        # --- 4. 竞品信息 ---
        competitors = _query_competitors(market_code, db)

        # --- 5. 历史策划 ---
        historical_plans = _query_historical_plans(market_code, db)

        # --- 6. 成本基准 ---
        cost_benchmarks = _query_cost_benchmarks(market_code, db)

        # --- 构建最终上下文 ---
        context: Dict[str, Any] = {
            "market_info": market_info,
            "energy_standards": energy_standards,
            "market_requirements": market_requirements,
            "competitors": competitors,
            "historical_plans": historical_plans,
            "cost_benchmarks": cost_benchmarks,
        }

        # --- 7. 补充字段（管理员手动录入）---
        if supplementary_analysis:
            context["supplementary"] = supplementary_analysis

        return context

    finally:
        if own_session:
            db.close()
