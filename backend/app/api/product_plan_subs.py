"""ProductPlan 子表 CRUD API — 4个子表的增删改查

Endpoints under prefix /api/product-plans (router prefix=/product-plans, included with prefix=/api):
- GET    /{plan_id}/initation      获取立项信息
- PUT    /{plan_id}/initation      创建/更新立项信息
- GET    /{plan_id}/market         获取市场信息
- PUT    /{plan_id}/market         创建/更新市场信息
- GET    /{plan_id}/tech-spec      获取技术规格
- PUT    /{plan_id}/tech-spec      创建/更新技术规格
- GET    /{plan_id}/team           获取团队成员列表
- POST   /{plan_id}/team           添加团队成员
- PUT    /{plan_id}/team/{id}      更新团队成员
- DELETE /{plan_id}/team/{id}      删除团队成员
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.permissions import require_menu
from app.models.product_plan import ProductPlan
from app.models.product_plan_subs import (
    ProductPlanInitiation,
    ProductPlanMarket,
    ProductPlanTechSpec,
    ProductPlanTeam,
)

router = APIRouter(prefix="/product-plans", tags=["产品策划子表"])


# ── Schemas ──

class InitiationCreate(BaseModel):
    product_type: Optional[str] = None
    target_market: Optional[str] = None
    climate_zone: Optional[str] = None
    refrigerant: Optional[str] = None
    capacity_range: Optional[str] = None
    voltage_freq: Optional[str] = None
    series_name: Optional[str] = None
    energy_rating: Optional[str] = None
    ip_ownership: Optional[str] = None
    project_duration: Optional[str] = None
    dev_category: Optional[str] = None
    project_origin: Optional[str] = None
    background_basis: Optional[str] = None
    overall_goal: Optional[str] = None
    tech_goal: Optional[str] = None
    cost_goal: Optional[str] = None
    sales_goal: Optional[str] = None
    cert_goal: Optional[str] = None
    schedule_goal: Optional[str] = None
    patent_goal: Optional[str] = None
    other_goals: Optional[str] = None
    deliverables: Optional[str] = None
    sample_qty: Optional[int] = None
    required_date: Optional[date] = None


class InitiationOut(BaseModel):
    id: int
    product_plan_id: str
    product_type: Optional[str] = None
    target_market: Optional[str] = None
    climate_zone: Optional[str] = None
    refrigerant: Optional[str] = None
    capacity_range: Optional[str] = None
    voltage_freq: Optional[str] = None
    series_name: Optional[str] = None
    energy_rating: Optional[str] = None
    ip_ownership: Optional[str] = None
    project_duration: Optional[str] = None
    dev_category: Optional[str] = None
    project_origin: Optional[str] = None
    background_basis: Optional[str] = None
    overall_goal: Optional[str] = None
    tech_goal: Optional[str] = None
    cost_goal: Optional[str] = None
    sales_goal: Optional[str] = None
    cert_goal: Optional[str] = None
    schedule_goal: Optional[str] = None
    patent_goal: Optional[str] = None
    other_goals: Optional[str] = None
    deliverables: Optional[str] = None
    sample_qty: Optional[int] = None
    required_date: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class MarketCreate(BaseModel):
    main_capacity: Optional[str] = None
    energy_efficiency_req: Optional[str] = None
    cert_requirements: Optional[str] = None
    target_price: Optional[str] = None
    customer_requirements: Optional[str] = None


class MarketOut(BaseModel):
    id: int
    product_plan_id: str
    main_capacity: Optional[str] = None
    energy_efficiency_req: Optional[str] = None
    cert_requirements: Optional[str] = None
    target_price: Optional[str] = None
    customer_requirements: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TechSpecCreate(BaseModel):
    core_performance: Optional[str] = None
    safety_compliance: Optional[str] = None
    optional_config: Optional[str] = None


class TechSpecOut(BaseModel):
    id: int
    product_plan_id: str
    core_performance: Optional[str] = None
    safety_compliance: Optional[str] = None
    optional_config: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    role_name: str
    member_name: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None


class TeamUpdate(BaseModel):
    role_name: Optional[str] = None
    member_name: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None


class TeamOut(BaseModel):
    id: int
    product_plan_id: str
    role_name: str
    member_name: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Helper ──

def _get_plan_or_404(db: Session, plan_id: str) -> ProductPlan:
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    return plan


# ── Initiation ──

@router.get("/{plan_id}/initiation", response_model=InitiationOut)
def get_initiation(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """获取立项信息"""
    _get_plan_or_404(db, plan_id)
    initiation = db.query(ProductPlanInitiation).filter(
        ProductPlanInitiation.product_plan_id == plan_id
    ).first()
    if not initiation:
        raise HTTPException(status_code=404, detail="立项信息不存在")
    return initiation


@router.put("/{plan_id}/initiation", response_model=InitiationOut)
def upsert_initiation(
    plan_id: str,
    data: InitiationCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """创建或更新立项信息"""
    _get_plan_or_404(db, plan_id)
    initiation = db.query(ProductPlanInitiation).filter(
        ProductPlanInitiation.product_plan_id == plan_id
    ).first()
    if initiation:
        for key, val in data.model_dump(exclude_unset=True).items():
            if val is not None:
                setattr(initiation, key, val)
    else:
        initiation = ProductPlanInitiation(
            product_plan_id=plan_id, **data.model_dump(exclude_unset=True)
        )
        db.add(initiation)
    db.commit()
    db.refresh(initiation)
    return initiation


# ── Market ──

@router.get("/{plan_id}/market", response_model=MarketOut)
def get_market(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """获取市场信息"""
    _get_plan_or_404(db, plan_id)
    market = db.query(ProductPlanMarket).filter(
        ProductPlanMarket.product_plan_id == plan_id
    ).first()
    if not market:
        raise HTTPException(status_code=404, detail="市场信息不存在")
    return market


@router.put("/{plan_id}/market", response_model=MarketOut)
def upsert_market(
    plan_id: str,
    data: MarketCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """创建或更新市场信息"""
    _get_plan_or_404(db, plan_id)
    market = db.query(ProductPlanMarket).filter(
        ProductPlanMarket.product_plan_id == plan_id
    ).first()
    if market:
        for key, val in data.model_dump(exclude_unset=True).items():
            if val is not None:
                setattr(market, key, val)
    else:
        market = ProductPlanMarket(
            product_plan_id=plan_id, **data.model_dump(exclude_unset=True)
        )
        db.add(market)
    db.commit()
    db.refresh(market)
    return market


# ── Tech Spec ──

@router.get("/{plan_id}/tech-spec", response_model=TechSpecOut)
def get_tech_spec(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """获取技术规格"""
    _get_plan_or_404(db, plan_id)
    tech = db.query(ProductPlanTechSpec).filter(
        ProductPlanTechSpec.product_plan_id == plan_id
    ).first()
    if not tech:
        raise HTTPException(status_code=404, detail="技术规格不存在")
    return tech


@router.put("/{plan_id}/tech-spec", response_model=TechSpecOut)
def upsert_tech_spec(
    plan_id: str,
    data: TechSpecCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """创建或更新技术规格"""
    _get_plan_or_404(db, plan_id)
    tech = db.query(ProductPlanTechSpec).filter(
        ProductPlanTechSpec.product_plan_id == plan_id
    ).first()
    if tech:
        for key, val in data.model_dump(exclude_unset=True).items():
            if val is not None:
                setattr(tech, key, val)
    else:
        tech = ProductPlanTechSpec(
            product_plan_id=plan_id, **data.model_dump(exclude_unset=True)
        )
        db.add(tech)
    db.commit()
    db.refresh(tech)
    return tech


# ── Team ──

@router.get("/{plan_id}/team", response_model=list[TeamOut])
def list_team_members(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """获取团队成员列表"""
    _get_plan_or_404(db, plan_id)
    members = db.query(ProductPlanTeam).filter(
        ProductPlanTeam.product_plan_id == plan_id
    ).all()
    return members


@router.post("/{plan_id}/team", response_model=TeamOut, status_code=201)
def add_team_member(
    plan_id: str,
    data: TeamCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """添加团队成员"""
    _get_plan_or_404(db, plan_id)
    member = ProductPlanTeam(product_plan_id=plan_id, **data.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/{plan_id}/team/{member_id}", response_model=TeamOut)
def update_team_member(
    plan_id: str,
    member_id: int,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """更新团队成员"""
    _get_plan_or_404(db, plan_id)
    member = db.query(ProductPlanTeam).filter(
        ProductPlanTeam.id == member_id,
        ProductPlanTeam.product_plan_id == plan_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="团队成员不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        if val is not None:
            setattr(member, key, val)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{plan_id}/team/{member_id}")
def delete_team_member(
    plan_id: str,
    member_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
):
    """删除团队成员"""
    _get_plan_or_404(db, plan_id)
    member = db.query(ProductPlanTeam).filter(
        ProductPlanTeam.id == member_id,
        ProductPlanTeam.product_plan_id == plan_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="团队成员不存在")
    db.delete(member)
    db.commit()
    return {"ok": True}
