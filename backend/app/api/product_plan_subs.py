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
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.database import get_db
from app.core.permissions import require_menu
from app.models.product_plan import ProductPlan, ProductPlanProjectLink
from app.models.product_plan_subs import (
    ProductPlanInitiation,
    ProductPlanMarket,
    ProductPlanTechSpec,
    ProductPlanTeam,
)
from app.schemas.product_plan_link import ProductPlanLinkCreate, ProductPlanLinkUpdate, ProductPlanLinkOut

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
    version_id: Optional[int] = None


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
    created_at: Optional[datetime] = None
    version_id: int = 1

    class Config:
        from_attributes = True


class MarketCreate(BaseModel):
    main_capacity: Optional[str] = None
    energy_efficiency_req: Optional[str] = None
    cert_requirements: Optional[str] = None
    target_price: Optional[str] = None
    customer_requirements: Optional[str] = None
    version_id: Optional[int] = None


class MarketOut(BaseModel):
    id: int
    product_plan_id: str
    main_capacity: Optional[str] = None
    energy_efficiency_req: Optional[str] = None
    cert_requirements: Optional[str] = None
    target_price: Optional[str] = None
    customer_requirements: Optional[str] = None
    created_at: Optional[datetime] = None
    version_id: int = 1

    class Config:
        from_attributes = True


class TechSpecCreate(BaseModel):
    core_performance: Optional[str] = None
    safety_compliance: Optional[str] = None
    optional_config: Optional[str] = None
    version_id: Optional[int] = None


class TechSpecOut(BaseModel):
    id: int
    product_plan_id: str
    core_performance: Optional[str] = None
    safety_compliance: Optional[str] = None
    optional_config: Optional[str] = None
    created_at: Optional[datetime] = None
    version_id: int = 1

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    role_name: Optional[str] = None
    member_name: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class TeamOut(BaseModel):
    id: int
    product_plan_id: str
    role_name: Optional[str] = None
    member_name: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    version_id: int = 1

    class Config:
        from_attributes = True


class TeamUpdate(BaseModel):
    role_name: Optional[str] = None
    member_name: Optional[str] = None
    department: Optional[str] = None
    responsibility: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    version_id: Optional[int] = None


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
    version: Optional[int] = Query(None, description="指定版本查询"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取立项信息"""
    _get_plan_or_404(db, plan_id)
    initiation = db.query(ProductPlanInitiation).filter(
        ProductPlanInitiation.product_plan_id == plan_id
    ).first()
    if not initiation:
        raise HTTPException(status_code=404, detail="立项信息不存在")
    if version is not None:
        if initiation.version_id != version:
            raise HTTPException(412, detail=f"版本已变更(当前{initiation.version_id}，请求{version})，请刷新")
    return initiation


@router.put("/{plan_id}/initiation", response_model=InitiationOut)
def upsert_initiation(
    plan_id: str,
    data: InitiationCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """创建或更新立项信息"""
    plan = _get_plan_or_404(db, plan_id)
    initiation = db.query(ProductPlanInitiation).filter(
        ProductPlanInitiation.product_plan_id == plan_id
    ).first()
    if initiation:
        # 可选乐观锁: 如果请求体传了 version_id 则做冲突检查
        if data.version_id is not None and data.version_id != initiation.version_id:
            raise HTTPException(409, detail="版本冲突，请刷新后重试")
        for key, val in data.model_dump(exclude_unset=True, exclude={'version_id'}).items():
            if val is not None:
                setattr(initiation, key, val)
        initiation.version_id = (initiation.version_id or 0) + 1
    else:
        initiation = ProductPlanInitiation(
            product_plan_id=plan_id, **data.model_dump(exclude_unset=True, exclude={'version_id'})
        )
        db.add(initiation)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(initiation)
    return initiation


# ── Market ──

@router.get("/{plan_id}/market", response_model=MarketOut)
def get_market(
    plan_id: str,
    version: Optional[int] = Query(None, description="指定版本查询"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取市场信息"""
    _get_plan_or_404(db, plan_id)
    market = db.query(ProductPlanMarket).filter(
        ProductPlanMarket.product_plan_id == plan_id
    ).first()
    if not market:
        raise HTTPException(status_code=404, detail="市场信息不存在")
    if version is not None:
        if market.version_id != version:
            raise HTTPException(412, detail=f"版本已变更(当前{market.version_id}，请求{version})，请刷新")
    return market


@router.put("/{plan_id}/market", response_model=MarketOut)
def upsert_market(
    plan_id: str,
    data: MarketCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """创建或更新市场信息"""
    plan = _get_plan_or_404(db, plan_id)
    market = db.query(ProductPlanMarket).filter(
        ProductPlanMarket.product_plan_id == plan_id
    ).first()
    if market:
        # 可选乐观锁: 如果请求体传了 version_id 则做冲突检查
        if data.version_id is not None and data.version_id != market.version_id:
            raise HTTPException(409, detail="版本冲突，请刷新后重试")
        for key, val in data.model_dump(exclude_unset=True, exclude={'version_id'}).items():
            if val is not None:
                setattr(market, key, val)
        market.version_id = (market.version_id or 0) + 1
    else:
        market = ProductPlanMarket(
            product_plan_id=plan_id, **data.model_dump(exclude_unset=True, exclude={'version_id'})
        )
        db.add(market)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(market)
    return market


# ── Tech Spec ──

@router.get("/{plan_id}/tech-spec", response_model=TechSpecOut)
def get_tech_spec(
    plan_id: str,
    version: Optional[int] = Query(None, description="指定版本查询"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取技术规格"""
    _get_plan_or_404(db, plan_id)
    tech = db.query(ProductPlanTechSpec).filter(
        ProductPlanTechSpec.product_plan_id == plan_id
    ).first()
    if not tech:
        raise HTTPException(status_code=404, detail="技术规格不存在")
    if version is not None:
        if tech.version_id != version:
            raise HTTPException(412, detail=f"版本已变更(当前{tech.version_id}，请求{version})，请刷新")
    return tech


@router.put("/{plan_id}/tech-spec", response_model=TechSpecOut)
def upsert_tech_spec(
    plan_id: str,
    data: TechSpecCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """创建或更新技术规格"""
    plan = _get_plan_or_404(db, plan_id)
    tech = db.query(ProductPlanTechSpec).filter(
        ProductPlanTechSpec.product_plan_id == plan_id
    ).first()
    if tech:
        # 可选乐观锁: 如果请求体传了 version_id 则做冲突检查
        if data.version_id is not None and data.version_id != tech.version_id:
            raise HTTPException(409, detail="版本冲突，请刷新后重试")
        for key, val in data.model_dump(exclude_unset=True, exclude={'version_id'}).items():
            if val is not None:
                setattr(tech, key, val)
        tech.version_id = (tech.version_id or 0) + 1
    else:
        tech = ProductPlanTechSpec(
            product_plan_id=plan_id, **data.model_dump(exclude_unset=True, exclude={'version_id'})
        )
        db.add(tech)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tech)
    return tech


# ── Team ──

@router.get("/{plan_id}/team", response_model=list[TeamOut])
def list_team_members(
    plan_id: str,
    version: Optional[int] = Query(None, description="指定版本查询"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> list:
    """获取团队成员列表"""
    _get_plan_or_404(db, plan_id)
    members = db.query(ProductPlanTeam).filter(
        ProductPlanTeam.product_plan_id == plan_id
    ).all()
    if version is not None and members:
        if members[0].version_id != version:
            raise HTTPException(412, detail=f"版本已变更(当前{members[0].version_id}，请求{version})，请刷新")
    return members


@router.post("/{plan_id}/team", response_model=TeamOut, status_code=201)
def add_team_member(
    plan_id: str,
    data: TeamCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """添加团队成员"""
    plan = _get_plan_or_404(db, plan_id)
    member = ProductPlanTeam(product_plan_id=plan_id, **data.model_dump())
    db.add(member)
    # 同步父表更新时间（单次 commit，避免部分写入风险）
    plan.updated_at = datetime.utcnow()
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
) -> dict:
    """更新团队成员"""
    _get_plan_or_404(db, plan_id)
    member = db.query(ProductPlanTeam).filter(
        ProductPlanTeam.id == member_id,
        ProductPlanTeam.product_plan_id == plan_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="团队成员不存在")
    # 可选乐观锁: 如果请求体传了 version_id 则做冲突检查
    if data.version_id is not None and data.version_id != member.version_id:
        raise HTTPException(409, detail="版本冲突，请刷新后重试")
    for key, val in data.model_dump(exclude_unset=True, exclude={'version_id'}).items():
        if val is not None:
            setattr(member, key, val)
    member.version_id = (member.version_id or 0) + 1
    member.product_plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{plan_id}/team/{member_id}")
def delete_team_member(
    plan_id: str,
    member_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """删除团队成员"""
    _get_plan_or_404(db, plan_id)
    member = db.query(ProductPlanTeam).filter(
        ProductPlanTeam.id == member_id,
        ProductPlanTeam.product_plan_id == plan_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="团队成员不存在")
    # 同步父表更新时间
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if plan:
        plan.updated_at = datetime.utcnow()
    db.delete(member)
    db.commit()
    return {"ok": True}


# ═══════════════ 项目关联 (Project Links) ═══════════════


@router.get("/{plan_id}/project-links", response_model=list[ProductPlanLinkOut])
def list_project_links(
    plan_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> list[ProductPlanLinkOut]:
    """获取策划关联的项目列表"""
    _get_plan_or_404(db, plan_id)
    links = db.query(ProductPlanProjectLink).filter(
        ProductPlanProjectLink.product_plan_id == plan_id,
    ).all()
    return [ProductPlanLinkOut.model_validate(l) for l in links]


@router.post("/{plan_id}/project-links", response_model=ProductPlanLinkOut, status_code=201)
def create_project_link(
    plan_id: str,
    data: ProductPlanLinkCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> ProductPlanLinkOut:
    """创建策划-项目关联"""
    _get_plan_or_404(db, plan_id)
    link = ProductPlanProjectLink(
        product_plan_id=plan_id,
        project_id=data.project_id,
        link_type=data.link_type,
        snapshot_data=data.snapshot_data,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return ProductPlanLinkOut.model_validate(link)


@router.put("/{plan_id}/project-links/{link_id}", response_model=ProductPlanLinkOut)
def update_project_link(
    plan_id: str,
    link_id: int,
    data: ProductPlanLinkUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> ProductPlanLinkOut:
    """更新项目关联类型/快照"""
    _get_plan_or_404(db, plan_id)
    link = db.query(ProductPlanProjectLink).filter(
        ProductPlanProjectLink.id == link_id,
        ProductPlanProjectLink.product_plan_id == plan_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="项目关联不存在")
    link.link_type = data.link_type
    link.snapshot_data = data.snapshot_data
    db.commit()
    db.refresh(link)
    return ProductPlanLinkOut.model_validate(link)


@router.delete("/{plan_id}/project-links/{link_id}")
def delete_project_link(
    plan_id: str,
    link_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """删除项目关联"""
    _get_plan_or_404(db, plan_id)
    link = db.query(ProductPlanProjectLink).filter(
        ProductPlanProjectLink.id == link_id,
        ProductPlanProjectLink.product_plan_id == plan_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="项目关联不存在")
    db.delete(link)
    db.commit()
    return {"ok": True}
