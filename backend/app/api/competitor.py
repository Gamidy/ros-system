"""竞品参数库 API — 竞品机型查询 & 对标分析"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.competitor import CompetitorModel

router = APIRouter(prefix="/pm", tags=["竞品库"])


# ── Pydantic Schemas ──────────────────────────────────────────────

class CompetitorCreate(BaseModel):
    brand: str = Field(..., max_length=80)
    model: str = Field(..., max_length=120)
    market: str = Field(..., max_length=80)
    product_type: Optional[str] = Field(None, max_length=60)
    cooling_capacity: Optional[str] = Field(None, max_length=40)
    cooling_capacity_w: Optional[int] = None
    heating_capacity_w: Optional[int] = None
    energy_rating: Optional[str] = Field(None, max_length=40)
    cooling_w: Optional[int] = None
    heating_w: Optional[int] = None
    eer: Optional[float] = None
    cspf: Optional[float] = None
    noise_indoor_db: Optional[float] = None
    noise_outdoor_db: Optional[float] = None
    airflow_m3h: Optional[float] = None
    indoor_size_mm: Optional[str] = Field(None, max_length=60)
    outdoor_size_mm: Optional[str] = Field(None, max_length=60)
    factory_price: Optional[str] = Field(None, max_length=60)
    launch_year: Optional[int] = None
    notes: Optional[str] = None


class CompetitorUpdate(BaseModel):
    brand: Optional[str] = Field(None, max_length=80)
    model: Optional[str] = Field(None, max_length=120)
    market: Optional[str] = Field(None, max_length=80)
    product_type: Optional[str] = Field(None, max_length=60)
    cooling_capacity: Optional[str] = Field(None, max_length=40)
    cooling_capacity_w: Optional[int] = None
    heating_capacity_w: Optional[int] = None
    energy_rating: Optional[str] = Field(None, max_length=40)
    cooling_w: Optional[int] = None
    heating_w: Optional[int] = None
    eer: Optional[float] = None
    cspf: Optional[float] = None
    noise_indoor_db: Optional[float] = None
    noise_outdoor_db: Optional[float] = None
    airflow_m3h: Optional[float] = None
    indoor_size_mm: Optional[str] = Field(None, max_length=60)
    outdoor_size_mm: Optional[str] = Field(None, max_length=60)
    factory_price: Optional[str] = Field(None, max_length=60)
    launch_year: Optional[int] = None
    notes: Optional[str] = None


# ── 市场能效标准定义 ──────────────────────────────────────────────
# 不同市场使用不同的能效指标（按具体国家）
# 优先从 markets 表读取，若失败则用此字典 fallback
MARKET_ENERGY_STANDARDS_FALLBACK = {
    # 东南亚
    "越南":       {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "印度尼西亚": {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "马来西亚":   {"param_key": "cspf",  "label": "APF",   "unit": "W/W",    "type": "seasonal"},
    "巴基斯坦":   {"param_key": "cspf",  "label": "APF",   "unit": "W/W",    "type": "seasonal"},
    # 中亚
    "乌兹别克斯坦": {"param_key": "eer", "label": "EER",   "unit": "W/W",    "type": "single"},
    "吉尔吉斯斯坦": {"param_key": "seer", "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "塔吉克斯坦":   {"param_key": "eer", "label": "EER",   "unit": "W/W",    "type": "single"},
    # 中东（GCC + 其他）
    "沙特":     {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "阿联酋":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "科威特":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "巴林":     {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "以色列":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "伊朗":     {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "伊拉克":   {"param_key": "eer",   "label": "EER",   "unit": "BTU/Wh", "type": "single"},
    # 美洲
    "美国":     {"param_key": "seer",  "label": "SEER2", "unit": "BTU/Wh", "type": "seasonal"},
    "加拿大":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "墨西哥":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "哥伦比亚": {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "巴西":     {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "阿根廷":   {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    # 欧洲
    "俄罗斯":   {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
    "白俄罗斯": {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
    "乌克兰":   {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "英国":     {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    # 独联体
    "阿塞拜疆": {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
    # 非洲
    "南非":     {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
    "阿尔及利亚": {"param_key": "eer", "label": "EER",   "unit": "W/W",    "type": "single"},
    "尼日利亚": {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
}
DEFAULT_ENERGY_KEY = "eer"


def _load_energy_standards_from_db(db) -> dict:
    """从 markets 表加载能效标准（优先使用）"""
    from app.models.product import Market
    try:
        items = db.query(Market).filter(
            Market.is_active == 'true',
            Market.energy_standard.isnot(None),
        ).all()
        result = {}
        for m in items:
            result[m.name] = {
                "param_key": m.energy_standard,
                "label": m.energy_label or m.energy_standard.upper(),
                "unit": m.energy_unit or "",
                "type": "seasonal" if m.energy_standard in ("cspf", "iseer", "seer") else "single",
            }
        return result or MARKET_ENERGY_STANDARDS_FALLBACK
    except Exception:
        return MARKET_ENERGY_STANDARDS_FALLBACK


def get_energy_standards(db=None) -> dict:
    """获取能效标准映射，优先DB，fallback到字典"""
    if db is not None:
        try:
            db_standards = _load_energy_standards_from_db(db)
            if db_standards:
                return db_standards
        except Exception:
            pass
    return MARKET_ENERGY_STANDARDS_FALLBACK


def get_energy_param_label(market: str, db=None) -> str:
    """获取市场对应的能效参数名"""
    std = get_energy_standards(db).get(market)
    if std:
        return std["label"]
    return "EER"


def get_energy_param_key(market: str, db=None) -> str:
    """获取市场对应的能效参数字段名"""
    std = get_energy_standards(db).get(market)
    if std:
        return std["param_key"]
    return DEFAULT_ENERGY_KEY


# ── 核心参数定义 ──────────────────────────────────────────────────
# 所有市场的通用参数
BASE_PARAM_NAMES = [
    {"key": "cooling_capacity_w", "label": "制冷量",         "unit": "W"},
    {"key": "heating_capacity_w", "label": "制热量",         "unit": "W"},
    {"key": "cooling_w",          "label": "制冷功率",       "unit": "W"},
    {"key": "heating_w",          "label": "制热功率",       "unit": "W"},
    {"key": "noise_indoor_db",    "label": "室内噪音",       "unit": "dB"},
    {"key": "noise_outdoor_db",   "label": "室外噪音",       "unit": "dB"},
    {"key": "airflow_m3h",        "label": "循环风量",       "unit": "m³/h"},
    {"key": "indoor_size_mm",     "label": "内机尺寸",       "unit": "mm"},
    {"key": "outdoor_size_mm",    "label": "外机尺寸",       "unit": "mm"},
    {"key": "factory_price",      "label": "出厂价",         "unit": ""},
    {"key": "launch_year",        "label": "上市年份",       "unit": ""},
    {"key": "energy_rating",      "label": "能效等级",       "unit": ""},
]

# 能效参数（市场差异化）
ENERGY_PARAM_TEMPLATE = {"key": "eer", "label": "EER", "unit": ""}


def get_param_names(market: str) -> list:
    """根据市场返回完整参数列表（含市场适配的能效参数）"""
    params = list(BASE_PARAM_NAMES)
    # 在市场对应的位置插入能效参数（放在能效等级前面）
    energy_label = get_energy_param_label(market)
    params.append({
        "key": get_energy_param_key(market),
        "label": energy_label,
        "unit": "W/W" if energy_label in ("CSPF", "ISEER", "SEER") else "",
    })
    return params


# ── 字段完整性校验 ────────────────────────────────────────────────
# 必填字段列表（用于校验竞品数据是否完整）
REQUIRED_FIELDS = [
    "brand", "model", "market", "product_type", "cooling_capacity",
    "cooling_capacity_w", "heating_capacity_w",
    "energy_rating", "cooling_w", "heating_w",
    "noise_indoor_db", "noise_outdoor_db", "airflow_m3h",
    "indoor_size_mm", "outdoor_size_mm", "factory_price", "launch_year",
]


def check_competitor_completeness(item: CompetitorModel) -> dict:
    """检查单条竞品数据的完整性，返回 {is_complete, missing_fields}"""
    missing = []
    for field in REQUIRED_FIELDS:
        val = getattr(item, field, None)
        if val is None or val == "":
            missing.append(field)
    # 同时检查对应市场的能效字段
    energy_key = get_energy_param_key(item.market)
    if energy_key not in REQUIRED_FIELDS:
        e_val = getattr(item, energy_key, None)
        if e_val is None or e_val == "":
            missing.append(energy_key)
    return {
        "is_complete": len(missing) == 0,
        "missing_fields": missing,
    }


def get_efficiency_value(item: CompetitorModel, market: str):
    """获取市场对应的能效值"""
    key = get_energy_param_key(market)
    return getattr(item, key, None)


# ── 序列化辅助 ────────────────────────────────────────────────────

def _serialize(item: CompetitorModel) -> dict:
    completeness = check_competitor_completeness(item)
    eff_value = get_efficiency_value(item, item.market)
    energy_label = get_energy_param_label(item.market)
    return {
        "id": item.id,
        "brand": item.brand,
        "model": item.model,
        "market": item.market,
        "product_type": item.product_type,
        "cooling_capacity": item.cooling_capacity,
        "cooling_capacity_w": item.cooling_capacity_w,
        "heating_capacity_w": item.heating_capacity_w,
        "energy_rating": item.energy_rating,
        "cooling_w": item.cooling_w,
        "heating_w": item.heating_w,
        "eer": item.eer,
        "cspf": item.cspf,
        "noise_indoor_db": item.noise_indoor_db,
        "noise_outdoor_db": item.noise_outdoor_db,
        "airflow_m3h": item.airflow_m3h,
        "indoor_size_mm": item.indoor_size_mm,
        "outdoor_size_mm": item.outdoor_size_mm,
        "factory_price": item.factory_price,
        "launch_year": item.launch_year,
        "notes": item.notes,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        # 市场适配的能效值
        "efficiency_value": eff_value,
        "efficiency_label": energy_label,
        "efficiency_key": get_energy_param_key(item.market),
        # 完整性状态
        "is_complete": completeness["is_complete"],
        "missing_fields": completeness["missing_fields"],
    }


# ── 市场列表（含能效标准）────────────────────────────────────────

@router.get("/markets")
def list_markets_with_standards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回所有激活的市场列表（含能效标准），用于前端下拉"""
    from app.models.product import Market
    items = db.query(Market).filter(
        Market.is_active == 'true',
        Market.energy_standard.isnot(None),
        Market.energy_standard != '',
    ).order_by(Market.region, Market.code).all()
    return [
        {
            "code": m.code,
            "name": m.name,
            "region": m.region,
            "energy_standard": m.energy_standard or "eer",
            "energy_label": m.energy_label or "EER",
            "energy_unit": m.energy_unit or "",
        }
        for m in items
    ]


@router.get("/markets/all")
def list_all_markets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回全部市场（含激活和停用的），PM管理用"""
    from app.models.product import Market
    items = db.query(Market).order_by(Market.region, Market.code).all()
    return [
        {
            "code": m.code,
            "name": m.name,
            "region": m.region or "",
            "energy_standard": m.energy_standard or "",
            "energy_label": m.energy_label or "",
            "energy_unit": m.energy_unit or "",
            "is_active": m.is_active or "true",
        }
        for m in items
    ]


@router.post("/markets")
def create_market(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
):
    """新增市场"""
    from app.models.product import Market
    code = data.get("code", "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="市场代码不能为空")
    existing = db.query(Market).filter(Market.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"市场代码 {code} 已存在")
    m = Market(
        code=code,
        name=data.get("name", code),
        region=data.get("region", ""),
        energy_standard=data.get("energy_standard", "eer"),
        energy_label=data.get("energy_label", "EER"),
        energy_unit=data.get("energy_unit", ""),
        is_active=data.get("is_active", "true"),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"message": "新增成功", "code": m.code, "name": m.name}


@router.put("/markets/{code}")
def update_market(
    code: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
):
    """更新市场信息"""
    from app.models.product import Market
    m = db.query(Market).filter(Market.code == code).first()
    if not m:
        raise HTTPException(status_code=404, detail="市场不存在")
    for key in ("name", "region", "energy_standard", "energy_label", "energy_unit", "is_active"):
        if key in data:
            setattr(m, key, data[key])
    db.commit()
    return {"message": "更新成功", "code": m.code, "name": m.name}


@router.delete("/markets/{code}")
def delete_market(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
):
    """删除市场"""
    from app.models.product import Market
    m = db.query(Market).filter(Market.code == code).first()
    if not m:
        raise HTTPException(status_code=404, detail="市场不存在")
    db.delete(m)
    db.commit()
    return {"message": "已删除"}


# ── 读取端点 ──────────────────────────────────────────────────────

@router.get("/competitors")
def list_competitors(
    market: Optional[str] = Query(None, description="目标市场过滤"),
    brand: Optional[str] = Query(None, description="品牌过滤"),
    capacity: Optional[str] = Query(None, alias="capacity", description="冷量段过滤"),
    energy_rating: Optional[str] = Query(None, description="能效等级过滤"),
    product_type: Optional[str] = Query(None, description="产品类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询竞品列表，支持 market/brand/capacity/energy_rating/product_type 过滤与分页（AND 交叉过滤）"""
    q = db.query(CompetitorModel)
    if market:
        q = q.filter(CompetitorModel.market == market)
    if brand:
        q = q.filter(CompetitorModel.brand == brand)
    if capacity:
        q = q.filter(CompetitorModel.cooling_capacity == capacity)
    if energy_rating:
        q = q.filter(CompetitorModel.energy_rating == energy_rating)
    if product_type:
        q = q.filter(CompetitorModel.product_type == product_type)

    total = q.count()
    items = q.order_by(CompetitorModel.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize(it) for it in items],
        "param_names": get_param_names(market) if market else BASE_PARAM_NAMES,
    }


@router.get("/competitors/{cid}")
def get_competitor(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单条竞品详情"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    return _serialize(item)


# ── 写入端点（admin / product_manager）────────────────────────────

@router.post("/competitors")
def create_competitor(
    data: CompetitorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
):
    """新增竞品记录"""
    item = CompetitorModel(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.put("/competitors/{cid}")
def update_competitor(
    cid: int,
    data: CompetitorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
):
    """更新竞品记录"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.delete("/competitors/{cid}")
def delete_competitor(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
):
    """删除竞品记录"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    db.delete(item)
    db.commit()
    return {"detail": "已删除"}


# ── 完整性校验端点 ────────────────────────────────────────────────

@router.get("/competitors/check-completeness")
def check_completeness(
    market: str = Query(..., description="目标市场"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查指定市场所有竞品数据的完整性"""
    items = db.query(CompetitorModel).filter(CompetitorModel.market == market).all()
    results = []
    all_complete = True
    for item in items:
        status = check_competitor_completeness(item)
        if not status["is_complete"]:
            all_complete = False
        results.append({
            "id": item.id,
            "brand": item.brand,
            "model": item.model,
            "is_complete": status["is_complete"],
            "missing_fields": status["missing_fields"],
        })
    return {
        "market": market,
        "all_complete": all_complete,
        "total": len(items),
        "details": results,
    }


# ── 对标查询 ──────────────────────────────────────────────────────

@router.get("/competitors/benchmark")
def benchmark_competitors(
    market: str = Query(..., description="目标市场（必填），如'越南'"),
    db: Session = Depends(get_db),
):
    """对标查询：返回指定市场下所有竞品的对比数据"""
    items = (
        db.query(CompetitorModel)
        .filter(CompetitorModel.market == market)
        .order_by(CompetitorModel.brand, CompetitorModel.model)
        .all()
    )
    return {
        "market": market,
        "competitors": [_serialize(it) for it in items],
        "param_names": get_param_names(market),
    }
