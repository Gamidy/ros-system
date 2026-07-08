"""产品主线API: Platform → Product → Version + ManufacturingVariant + Market"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_role, sanitize_dict, sanitize_html
from app.core.permissions import require_menu
from app.models.product import (
    Platform, Product, Version, VersionStatus, Market,
    ManufacturingVariant, product_market_table,
)
from app.models.user import User
from app.services.product_rules import product_rules
from app.schemas import (
    PlatformCreate, PlatformUpdate, PlatformOut,
    ProductCreate, ProductUpdate, ProductOut,
    VersionCreate, VersionStatusUpdate, VersionOut,
    ManufacturingVariantCreate, ManufacturingVariantOut,
    MarketCreate, MarketOut, ProductMarketAssign,
    VersionRuleRequest, VersionRuleResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["产品主线"])


# ══════════════════════════════════════════════════
# Market 字典管理（⚠️ 已废弃 — 请使用 /api/pm/markets 端点）
# ══════════════════════════════════════════════════

@router.get("/markets", response_model=list[MarketOut])
def list_markets(db: Session = Depends(get_db), _=Depends(require_menu("products"))) -> list[MarketOut]:
    """列出所有市场"""
    return db.query(Market).all()


@router.post("/markets", response_model=MarketOut)
def create_market(data: MarketCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> MarketOut:
    """添加新市场"""
    if db.query(Market).filter(Market.code == data.code.upper()).first():
        raise HTTPException(status_code=400, detail="市场代码已存在")
    d = sanitize_dict(data.model_dump())
    d["code"] = d["code"].upper()
    m = Market(**d)
    db.add(m); db.commit(); db.refresh(m)
    return m


# ══════════════════════════════════════════════════
# Version 产生规则引擎（无状态路由）
# ══════════════════════════════════════════════════

@router.post("/rules/evaluate-version", response_model=VersionRuleResponse)
def evaluate_version_change(data: VersionRuleRequest, _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> VersionRuleResponse:
    """评估变更是否需要创建新Version（PR-06, PR-09, PR-10）"""
    result = product_rules.evaluate_version_change(
        change_description=data.change_description,
        material_level=data.material_level,
        change_category=data.change_category,
        is_customer_perceivable=data.is_customer_perceivable,
    )
    return result.to_dict()


# ══════════════════════════════════════════════════
# Platform 管理
# ══════════════════════════════════════════════════

@router.get("/platforms", response_model=list[PlatformOut])
def list_platforms(
    platform_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_menu("products")),
) -> list[PlatformOut]:
    """列出所有平台，可按类型/状态筛选"""
    q = db.query(Platform)
    if platform_type:
        q = q.filter(Platform.platform_type == platform_type)
    if status:
        q = q.filter(Platform.status == status)
    return q.all()


@router.post("/platforms", response_model=PlatformOut)
def create_platform(data: PlatformCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> PlatformOut:
    """创建新平台（PR-02: 按结构尺寸定义）"""
    if db.query(Platform).filter(Platform.code == data.code).first():
        raise HTTPException(status_code=400, detail="平台编码已存在")
    p = Platform(**sanitize_dict(data.model_dump()))
    db.add(p); db.commit(); db.refresh(p)
    return p


@router.get("/platforms/{pid}", response_model=PlatformOut)
def get_platform(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("products"))) -> PlatformOut:
    p = db.query(Platform).filter(Platform.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="平台不存在")
    return p


@router.patch("/platforms/{pid}", response_model=PlatformOut)
def update_platform(pid: int, data: PlatformUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> PlatformOut:
    """更新平台信息"""
    p = db.query(Platform).filter(Platform.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="平台不存在")
    for k, v in sanitize_dict(data.model_dump(exclude_unset=True)).items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return p


# ══════════════════════════════════════════════════
# Product 管理
# ══════════════════════════════════════════════════

@router.get("", response_model=list[ProductOut])
def list_products(
    platform_id: Optional[int] = None,
    market: Optional[str] = None,
    capacity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_menu("products")),
) -> list[ProductOut]:
    """列出所有产品，可按平台/市场/容量筛选"""
    q = db.query(Product)
    if platform_id:
        q = q.filter(Product.platform_id == platform_id)
    if capacity:
        q = q.filter(Product.capacity == capacity)
    if status:
        q = q.filter(Product.status == status)
    # 市场筛选通过关联表
    if market:
        q = q.join(product_market_table).filter(product_market_table.c.market_code == market)
    products = q.all()
    return [_product_to_out(p) for p in products]


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> ProductOut:
    """创建新产品（PR-11: Product = Market × Capacity × Platform）"""
    if db.query(Product).filter(Product.code == data.code).first():
        raise HTTPException(status_code=400, detail="产品编码已存在")

    # 验证平台存在
    if not db.query(Platform).filter(Platform.id == data.platform_id).first():
        raise HTTPException(status_code=400, detail="主平台不存在")

    # 验证室内/室外平台（如果指定）
    if data.indoor_platform_id and not db.query(Platform).filter(
        Platform.id == data.indoor_platform_id, Platform.platform_type == "IDU"
    ).first():
        raise HTTPException(status_code=400, detail="室内平台不存在或类型不是IDU")
    if data.outdoor_platform_id and not db.query(Platform).filter(
        Platform.id == data.outdoor_platform_id, Platform.platform_type == "ODU"
    ).first():
        raise HTTPException(status_code=400, detail="室外平台不存在或类型不是ODU")

    # 编码格式验证
    if data.market and data.capacity:
        ok, msg = product_rules.validate_product_code(data.code, data.market, data.capacity)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)

    p = Product(**sanitize_dict(data.model_dump(exclude={"market"})))
    db.add(p)
    try:
        # 如果指定了市场，创建关联
        if data.market:
            db.flush()
            _ensure_market_exists(db, data.market.upper())
            db.execute(product_market_table.insert().values(
                product_id=p.id, market_code=data.market.upper()
            ))
        db.commit()
        db.refresh(p)
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        logger.error(f"产品创建失败: {e}")
        raise
    return _product_to_out(p)


@router.get("/{pid}", response_model=ProductOut)
def get_product(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("products"))) -> ProductOut:
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="产品不存在")
    return _product_to_out(p)


@router.patch("/{pid}", response_model=ProductOut)
def update_product(pid: int, data: ProductUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> ProductOut:
    """更新产品信息"""
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="产品不存在")
    for k, v in sanitize_dict(data.model_dump(exclude_unset=True)).items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return _product_to_out(p)


# ══════════════════════════════════════════════════
# Product ↔ Market 多对多管理
# ══════════════════════════════════════════════════

@router.post("/{pid}/markets", response_model=ProductOut)
def assign_markets(pid: int, data: ProductMarketAssign, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> ProductOut:
    """为产品分配目标市场（PR-08: Market ≠ Product, 多对多）"""
    p = db.query(Product).filter(Product.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 清除旧关联
    db.execute(product_market_table.delete().where(product_market_table.c.product_id == pid))
    # 添加新关联
    for code in data.market_codes:
        _ensure_market_exists(db, code.upper())
        db.execute(product_market_table.insert().values(
            product_id=pid, market_code=code.upper()
        ))
    db.commit(); db.refresh(p)
    return _product_to_out(p)


# ══════════════════════════════════════════════════
# Version 管理
# ══════════════════════════════════════════════════

@router.get("/{pid}/versions", response_model=list[VersionOut])
def list_versions(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("products"))) -> list[VersionOut]:
    """列出产品的所有版本"""
    if not db.query(Product).filter(Product.id == pid).first():
        raise HTTPException(status_code=404, detail="产品不存在")
    return db.query(Version).filter(Version.product_id == pid).order_by(Version.created_at.desc()).all()


@router.post("/{pid}/versions", response_model=VersionOut)
def create_version(pid: int, data: VersionCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> VersionOut:
    """创建产品新版本"""
    if not db.query(Product).filter(Product.id == pid).first():
        raise HTTPException(status_code=404, detail="产品不存在")

    # PR-09: 客户可感知变更标记
    v = Version(
        product_id=pid,
        version_no=data.version_no,
        reason=sanitize_html(data.reason) if data.reason else data.reason,
        change_type=sanitize_html(data.change_type) if data.change_type else data.change_type,
        customer_perceivable="true" if data.customer_perceivable else "false",
    )
    db.add(v); db.commit(); db.refresh(v)
    return v


@router.patch("/versions/{vid}/status", response_model=VersionOut)
def update_version_status(
    vid: int, data: VersionStatusUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))
) -> VersionOut:
    """更新Version生命周期状态（带转换校验）"""
    v = db.query(Version).filter(Version.id == vid).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")

    try:
        target_status = VersionStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效状态: {data.status}")

    # 验证转换是否合法
    ok, msg = product_rules.validate_version_transition(v.status, target_status)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    v.status = target_status
    db.commit(); db.refresh(v)
    return v


# ══════════════════════════════════════════════════
# Manufacturing Variant 管理
# ══════════════════════════════════════════════════

@router.post("/versions/{vid}/variants", response_model=ManufacturingVariantOut)
def create_variant(vid: int, data: ManufacturingVariantCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "systems_engineer"))) -> ManufacturingVariantOut:
    """
    创建制造变体（PR-10: Product Version ≠ MBOM Version）
    同一Version下不同工厂可有不同MBOM
    """
    v = db.query(Version).filter(Version.id == vid).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    if db.query(ManufacturingVariant).filter(
        ManufacturingVariant.version_id == vid,
        ManufacturingVariant.factory_code == data.factory_code
    ).first():
        raise HTTPException(status_code=400, detail="该工厂的变体已存在")
    mv = ManufacturingVariant(version_id=vid, **sanitize_dict(data.model_dump()))
    db.add(mv); db.commit(); db.refresh(mv)
    return mv


@router.get("/versions/{vid}/variants", response_model=list[ManufacturingVariantOut])
def list_variants(vid: int, db: Session = Depends(get_db), _=Depends(require_menu("products"))) -> list[ManufacturingVariantOut]:
    """列出版本的所有制造变体"""
    return db.query(ManufacturingVariant).filter(ManufacturingVariant.version_id == vid).all()


# ══════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════

def _product_to_out(p: Product) -> dict:
    """将Product ORM对象转为输出dict（包含markets列表）"""
    d = {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "platform_id": p.platform_id,
        "capacity": p.capacity,
        "indoor_platform_id": p.indoor_platform_id,
        "outdoor_platform_id": p.outdoor_platform_id,
        "status": p.status,
        "description": p.description,
        "market_codes": [m.code for m in p.markets] if p.markets else [],
        "created_at": p.created_at,
    }
    return d


def _ensure_market_exists(db: Session, code: str):
    """确保市场字典中存在该市场代码"""
    if not db.query(Market).filter(Market.code == code).first():
        db.add(Market(code=code, name=code))
