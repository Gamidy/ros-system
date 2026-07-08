"""竞品参数库 API — 竞品机型查询 & 对标分析"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.competitor import CompetitorModel
from app.models.competitor_version import CompetitorVersion
from app.services import event_bus

logger = logging.getLogger(__name__)

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
    unit_type: Optional[str] = Field(None, max_length=20)
    launch_year: Optional[int] = None
    notes: Optional[str] = None
    annual_sales: Optional[float] = None
    extra_fields: Optional[dict] = None
    image_urls: Optional[list] = None


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
    unit_type: Optional[str] = Field(None, max_length=20)
    launch_year: Optional[int] = None
    notes: Optional[str] = None
    annual_sales: Optional[float] = None
    extra_fields: Optional[dict] = None


# ── 市场能效标准定义 ──────────────────────────────────────────────

MARKET_ENERGY_STANDARDS_FALLBACK = {
    "越南":       {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "印度尼西亚": {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "马来西亚":   {"param_key": "cspf",  "label": "APF",   "unit": "W/W",    "type": "seasonal"},
    "巴基斯坦":   {"param_key": "cspf",  "label": "APF",   "unit": "W/W",    "type": "seasonal"},
    "乌兹别克斯坦": {"param_key": "eer", "label": "EER",   "unit": "W/W",    "type": "single"},
    "吉尔吉斯斯坦": {"param_key": "seer", "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "塔吉克斯坦":   {"param_key": "eer", "label": "EER",   "unit": "W/W",    "type": "single"},
    "沙特":     {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "阿联酋":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "科威特":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "巴林":     {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "以色列":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "伊朗":     {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "伊拉克":   {"param_key": "eer",   "label": "EER",   "unit": "BTU/Wh", "type": "single"},
    "美国":     {"param_key": "seer",  "label": "SEER2", "unit": "BTU/Wh", "type": "seasonal"},
    "加拿大":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "墨西哥":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "哥伦比亚": {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "巴西":     {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "阿根廷":   {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "俄罗斯":   {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
    "白俄罗斯": {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
    "乌克兰":   {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "英国":     {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "意大利":   {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "欧盟":     {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
    "阿塞拜疆": {"param_key": "eer",   "label": "EER",   "unit": "W/W",    "type": "single"},
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
    except Exception as e:
        logger.warning(f"从数据库加载能效标准失败: {e}")
        return MARKET_ENERGY_STANDARDS_FALLBACK


def get_energy_standards(db=None) -> dict:
    """获取能效标准映射，优先DB，fallback到字典"""
    if db is not None:
        try:
            db_standards = _load_energy_standards_from_db(db)
            if db_standards:
                return db_standards
        except Exception as e:
            logger.warning(f"从数据库加载能效标准(备选)失败: {e}")
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
    {"key": "unit_type",          "label": "单冷/冷暖",      "unit": ""},
    {"key": "launch_year",        "label": "上市年份",       "unit": ""},
    {"key": "energy_rating",      "label": "能效等级",       "unit": ""},
]

ENERGY_PARAM_TEMPLATE = {"key": "eer", "label": "EER", "unit": ""}


def get_param_names(market: str) -> list:
    """根据市场返回完整参数列表（含市场适配的能效参数）"""
    params = list(BASE_PARAM_NAMES)
    energy_label = get_energy_param_label(market)
    params.append({
        "key": get_energy_param_key(market),
        "label": energy_label,
        "unit": "W/W" if energy_label in ("CSPF", "ISEER", "SEER") else "",
    })
    return params


# ── 字段完整性校验 ────────────────────────────────────────────────

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
    energy_key = get_energy_param_key(item.market)
    if energy_key not in REQUIRED_FIELDS:
        e_val = getattr(item, energy_key, None)
        if e_val is None or e_val == "":
            missing.append(energy_key)
    return {"is_complete": len(missing) == 0, "missing_fields": missing}


def get_efficiency_value(item: CompetitorModel, market: str):
    """获取市场对应的能效值"""
    key = get_energy_param_key(market)
    return getattr(item, key, None)


# ── 序列化辅助 ────────────────────────────────────────────────────

def _serialize(item: CompetitorModel) -> dict:
    completeness = check_competitor_completeness(item)
    eff_value = get_efficiency_value(item, item.market)
    energy_label = get_energy_param_label(item.market)
    extra = item.extra_fields or {}
    if isinstance(extra, str):
        import json
        try:
            extra = json.loads(extra)
        except (json.JSONDecodeError, TypeError):
            extra = {}
    scop = extra.get("scop")
    heating_energy_rating = extra.get("heating_energy_rating")
    pdc = extra.get("pdc")
    pdh = extra.get("pdh")
    noise_indoor_power_db = extra.get("noise_indoor_power_db")
    noise_outdoor_power_db = extra.get("noise_outdoor_power_db")
    return {
        "id": item.id, "brand": item.brand, "model": item.model,
        "market": item.market, "product_type": item.product_type,
        "cooling_capacity": item.cooling_capacity,
        "cooling_capacity_w": item.cooling_capacity_w,
        "heating_capacity_w": item.heating_capacity_w,
        "energy_rating": item.energy_rating,
        "cooling_w": item.cooling_w, "heating_w": item.heating_w,
        "eer": item.eer, "cspf": item.cspf,
        "scop": scop, "heating_energy_rating": heating_energy_rating,
        "pdc": pdc, "pdh": pdh,
        "noise_indoor_db": item.noise_indoor_db,
        "noise_outdoor_db": item.noise_outdoor_db,
        "noise_indoor_power_db": noise_indoor_power_db,
        "noise_outdoor_power_db": noise_outdoor_power_db,
        "airflow_m3h": item.airflow_m3h,
        "indoor_size_mm": item.indoor_size_mm,
        "outdoor_size_mm": item.outdoor_size_mm,
        "factory_price": item.factory_price,
        "annual_sales": item.annual_sales,
        "unit_type": item.unit_type, "launch_year": item.launch_year,
        "notes": item.notes, "extra_fields": extra,
        "image_urls": item.image_urls or [],
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "efficiency_value": eff_value,
        "efficiency_label": energy_label,
        "efficiency_key": get_energy_param_key(item.market),
        "is_complete": completeness["is_complete"],
        "missing_fields": completeness["missing_fields"],
    }


# ── 版本快照辅助（供 competitor_history 使用）─────────────────────

TRACKED_FIELDS = [
    "brand", "model", "market", "product_type", "cooling_capacity",
    "cooling_capacity_w", "heating_capacity_w", "energy_rating",
    "cooling_w", "heating_w", "eer", "cspf",
    "noise_indoor_db", "noise_outdoor_db", "airflow_m3h",
    "indoor_size_mm", "outdoor_size_mm", "factory_price",
    "annual_sales", "unit_type",
    "launch_year", "notes", "extra_fields", "image_urls",
]


def _build_snapshot_data(item: CompetitorModel) -> dict:
    """将竞品模型构建为纯字典快照"""
    extra = item.extra_fields or {}
    if isinstance(extra, str):
        import json
        try:
            extra = json.loads(extra)
        except (json.JSONDecodeError, TypeError):
            extra = {}
    return {
        "brand": item.brand, "model": item.model,
        "market": item.market, "product_type": item.product_type,
        "cooling_capacity": item.cooling_capacity,
        "cooling_capacity_w": item.cooling_capacity_w,
        "heating_capacity_w": item.heating_capacity_w,
        "energy_rating": item.energy_rating,
        "cooling_w": item.cooling_w, "heating_w": item.heating_w,
        "eer": item.eer, "cspf": item.cspf,
        "noise_indoor_db": item.noise_indoor_db,
        "noise_outdoor_db": item.noise_outdoor_db,
        "airflow_m3h": item.airflow_m3h,
        "indoor_size_mm": item.indoor_size_mm,
        "outdoor_size_mm": item.outdoor_size_mm,
        "factory_price": item.factory_price,
        "annual_sales": item.annual_sales,
        "unit_type": item.unit_type, "launch_year": item.launch_year,
        "notes": item.notes, "extra_fields": extra,
        "image_urls": item.image_urls or [],
        "scop": extra.get("scop"),
        "heating_energy_rating": extra.get("heating_energy_rating"),
        "pdc": extra.get("pdc"), "pdh": extra.get("pdh"),
        "noise_indoor_power_db": extra.get("noise_indoor_power_db"),
        "noise_outdoor_power_db": extra.get("noise_outdoor_power_db"),
        "seer": extra.get("seer"),
    }


def _create_snapshot(
    db: Session,
    competitor: CompetitorModel,
    old_snapshot: dict | None,
    changed_by: str | None,
) -> CompetitorVersion:
    """创建竞品版本快照，计算新旧差异"""
    new_snapshot = _build_snapshot_data(competitor)
    changed_fields: dict[str, dict] = {}

    if old_snapshot:
        for field in TRACKED_FIELDS:
            old_val = old_snapshot.get(field)
            new_val = new_snapshot.get(field)
            if old_val != new_val:
                changed_fields[field] = {"old": old_val, "new": new_val}
    else:
        for field in TRACKED_FIELDS:
            val = new_snapshot.get(field)
            changed_fields[field] = {"old": None, "new": val}

    version = CompetitorVersion(
        competitor_id=competitor.id,
        changed_fields=changed_fields or None,
        snapshot_data=new_snapshot,
        changed_by=changed_by,
    )
    db.add(version)
    return version


# ── CRUD 端点 ──────────────────────────────────────────────────────

def _get_market_code(market_name: str, db: Session) -> str:
    """市场名称 → 市场代码"""
    from app.models.product import Market
    try:
        m = db.query(Market).filter(Market.name == market_name).first()
        if m:
            return m.code
    except Exception:
        pass
    NAME_TO_CODE = {
        "欧盟": "EU", "越南": "VN", "印度尼西亚": "ID", "马来西亚": "MY",
        "巴基斯坦": "PK", "乌兹别克斯坦": "UZ", "吉尔吉斯斯坦": "KG",
        "塔吉克斯坦": "TJ", "沙特": "SA", "阿联酋": "AE", "科威特": "KW",
        "巴林": "BH", "以色列": "IL", "伊朗": "IR", "伊拉克": "IQ",
        "美国": "US", "加拿大": "CA", "墨西哥": "MX", "哥伦比亚": "CO",
        "巴西": "BR", "阿根廷": "AR", "俄罗斯": "RU", "白俄罗斯": "BY",
        "乌克兰": "UA", "英国": "GB", "意大利": "IT", "阿塞拜疆": "AZ",
        "南非": "ZA", "阿尔及利亚": "DZ", "尼日利亚": "NG",
        "加纳": "GH", "澳大利亚": "AU",
    }
    return NAME_TO_CODE.get(market_name, "")


@router.get("/competitors")
def list_competitors(
    market: Optional[str] = Query(None, description="目标市场过滤"),
    brand: Optional[str] = Query(None, description="品牌过滤"),
    capacity: Optional[str] = Query(None, alias="capacity", description="冷量段过滤"),
    energy_rating: Optional[str] = Query(None, description="能效等级过滤"),
    product_type: Optional[str] = Query(None, description="产品类型过滤"),
    unit_type: Optional[str] = Query(None, description="单冷/冷暖过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """查询竞品列表，支持 market/brand/capacity/energy_rating/product_type 过滤与分页"""
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
    if unit_type:
        q = q.filter(CompetitorModel.unit_type == unit_type)

    total = q.count()
    items = q.order_by(CompetitorModel.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    param_configs = []
    if market:
        from app.models.market_param_config import MarketParamConfig
        configs = db.query(MarketParamConfig).filter(
            MarketParamConfig.market_code == _get_market_code(market, db),
            MarketParamConfig.is_active == "true",
        ).order_by(MarketParamConfig.sort_order).all()
        param_configs = [
            {"param_key": c.param_key, "param_label": c.param_label,
             "param_unit": c.param_unit or "", "data_type": c.data_type,
             "is_required": c.is_required == "true"}
            for c in configs
        ]

    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [_serialize(it) for it in items],
        "param_names": get_param_names(market) if market else BASE_PARAM_NAMES,
        "param_configs": param_configs,
    }


@router.get("/competitors/{cid}")
def get_competitor(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取单条竞品详情"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    return _serialize(item)


@router.post("/competitors")
def create_competitor(
    data: CompetitorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """新增竞品记录"""
    item = CompetitorModel(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    user_id = str(current_user.id) if hasattr(current_user, "id") else None
    event_bus.emit(
        event_type="competitor.created",
        payload={"id": item.id, "brand": item.brand, "model": item.model, "market": item.market},
        source="competitor", producer="competitor.service", user_id=user_id,
    )
    return _serialize(item)


@router.put("/competitors/{cid}")
def update_competitor(
    cid: int,
    data: CompetitorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """更新竞品记录（自动创建版本快照）"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")

    old_snapshot = _build_snapshot_data(item)
    changed_by = current_user.username if hasattr(current_user, "username") else str(current_user.id)

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    db.commit()
    db.refresh(item)

    _create_snapshot(db, item, old_snapshot, changed_by)
    db.commit()

    user_id = str(current_user.id) if hasattr(current_user, "id") else None
    event_bus.emit(
        event_type="competitor.updated",
        payload={"id": item.id, "brand": item.brand, "model": item.model, "market": item.market},
        source="competitor", producer="competitor.service", user_id=user_id,
    )
    return _serialize(item)


@router.delete("/competitors/{cid}")
def delete_competitor(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """删除竞品记录"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    db.delete(item)
    db.commit()
    return {"detail": "已删除"}
