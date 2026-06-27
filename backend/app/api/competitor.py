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


# ── 版本快照辅助 ──────────────────────────────────────────────────

# 需要跟踪变更的字段（不包含 id/created_at/updated_at 等系统字段）
TRACKED_FIELDS = [
    "brand", "model", "market", "product_type", "cooling_capacity",
    "cooling_capacity_w", "heating_capacity_w", "energy_rating",
    "cooling_w", "heating_w", "eer", "cspf",
    "noise_indoor_db", "noise_outdoor_db", "airflow_m3h",
    "indoor_size_mm", "outdoor_size_mm", "factory_price",
    "launch_year", "notes",
]


def _build_snapshot_data(item: CompetitorModel) -> dict:
    """将竞品模型构建为纯字典快照"""
    return {
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
        # 首次快照 — 所有字段视为新增
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


# ── 市场列表（含能效标准）────────────────────────────────────────

@router.get("/markets")
def list_markets_with_standards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
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
            "energy_standard_detail": m.energy_standard_detail,
            "national_standard": m.national_standard,
            "voltage_freq": m.voltage_freq,
            "cooling_max_temp": m.cooling_max_temp,
            "heating_min_temp": m.heating_min_temp,
            "structure_type": m.structure_type,
            "main_selling_model": m.main_selling_model,
            "refrigerant": m.refrigerant,
            "refrigerant_charge": m.refrigerant_charge,
        }
        for m in items
    ]


@router.get("/markets/all")
def list_all_markets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
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
            "energy_standard_detail": m.energy_standard_detail,
            "national_standard": m.national_standard,
            "voltage_freq": m.voltage_freq,
            "cooling_max_temp": m.cooling_max_temp,
            "heating_min_temp": m.heating_min_temp,
            "structure_type": m.structure_type,
            "main_selling_model": m.main_selling_model,
            "refrigerant": m.refrigerant,
            "refrigerant_charge": m.refrigerant_charge,
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
) -> dict:
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
        energy_standard_detail=data.get("energy_standard_detail"),
        national_standard=data.get("national_standard"),
        voltage_freq=data.get("voltage_freq"),
        cooling_max_temp=data.get("cooling_max_temp"),
        heating_min_temp=data.get("heating_min_temp"),
        structure_type=data.get("structure_type"),
        main_selling_model=data.get("main_selling_model"),
        refrigerant=data.get("refrigerant"),
        refrigerant_charge=data.get("refrigerant_charge"),
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
) -> dict:
    """更新市场信息"""
    from app.models.product import Market
    m = db.query(Market).filter(Market.code == code).first()
    if not m:
        raise HTTPException(status_code=404, detail="市场不存在")
    for key in ("name", "region", "energy_standard", "energy_label", "energy_unit",
                "energy_standard_detail", "national_standard", "voltage_freq",
                "cooling_max_temp", "heating_min_temp", "structure_type",
                "main_selling_model", "refrigerant", "refrigerant_charge", "is_active"):
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
) -> dict:
    """删除市场"""
    from app.models.product import Market
    m = db.query(Market).filter(Market.code == code).first()
    if not m:
        raise HTTPException(status_code=404, detail="市场不存在")
    # 检查是否有子记录
    from app.models.pm_config import MarketCertification, MarketCompressor
    from app.models.competitor import CompetitorModel
    cert_count = db.query(MarketCertification).filter(MarketCertification.market_code == code).count()
    comp_count = db.query(MarketCompressor).filter(MarketCompressor.market_code == code).count()
    comp_model_count = db.query(CompetitorModel).filter(CompetitorModel.market == m.name).count()
    if cert_count > 0 or comp_count > 0 or comp_model_count > 0:
        raise HTTPException(status_code=400, detail=f"该市场有 {cert_count} 条认证要求、{comp_count} 条压缩机信息、{comp_model_count} 条竞品数据，请先删除子记录")
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
) -> dict:
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
) -> dict:
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
) -> dict:
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
) -> dict:
    """更新竞品记录（自动创建版本快照）"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")

    # 更新前快照
    old_snapshot = _build_snapshot_data(item)
    changed_by = current_user.username if hasattr(current_user, "username") else str(current_user.id)

    # 应用更新
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    db.commit()
    db.refresh(item)

    # 自动创建版本快照
    _create_snapshot(db, item, old_snapshot, changed_by)
    db.commit()

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


# ── 版本快照 / 历史变更 ────────────────────────────────────────────


@router.post("/competitors/{cid}/snapshot")
def take_snapshot(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """手动记录当前竞品参数快照"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")

    # 获取上次快照用于计算差异
    last_version = (
        db.query(CompetitorVersion)
        .filter(CompetitorVersion.competitor_id == cid)
        .order_by(CompetitorVersion.created_at.desc())
        .first()
    )
    old_snapshot = last_version.snapshot_data if last_version else None
    changed_by = current_user.username if hasattr(current_user, "username") else str(current_user.id)

    version = _create_snapshot(db, item, old_snapshot, changed_by)
    db.commit()
    db.refresh(version)

    return {
        "id": version.id,
        "competitor_id": version.competitor_id,
        "changed_fields": version.changed_fields,
        "changed_by": version.changed_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.get("/competitors/{cid}/history")
def get_competitor_history(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """查看竞品的历史变更记录"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")

    versions = (
        db.query(CompetitorVersion)
        .filter(CompetitorVersion.competitor_id == cid)
        .order_by(CompetitorVersion.created_at.desc())
        .all()
    )

    return {
        "competitor_id": cid,
        "competitor": f"{item.brand} {item.model}",
        "total": len(versions),
        "versions": [
            {
                "id": v.id,
                "changed_fields": v.changed_fields,
                "snapshot_data": v.snapshot_data,
                "changed_by": v.changed_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


# ── 完整性校验端点 ────────────────────────────────────────────────

@router.get("/competitors/check-completeness")
def check_completeness(
    market: str = Query(..., description="目标市场"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
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
) -> dict:
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


# ══════════════════════════════════════════════════
# 市场认证要求 CRUD
# ══════════════════════════════════════════════════

@router.get("/markets/{code}/certifications")
def list_market_certifications(
    code: str,
    cert_type: Optional[str] = Query(None, description="按认证类型过滤: safety/energy/emc/environmental"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """列出指定市场的认证要求"""
    from app.models.pm_config import MarketCertification
    q = db.query(MarketCertification).filter(MarketCertification.market_code == code)
    if cert_type:
        q = q.filter(MarketCertification.cert_type == cert_type)
    items = q.order_by(MarketCertification.cert_type, MarketCertification.sort_order).all()
    return [
        {
            "id": c.id,
            "market_code": c.market_code,
            "cert_type": c.cert_type,
            "cert_standard": c.cert_standard,
            "description": c.description,
            "is_required": c.is_required,
            "sort_order": c.sort_order,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in items
    ]


@router.post("/markets/{code}/certifications")
def create_market_certification(
    code: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """新增市场认证要求"""
    from app.models.pm_config import MarketCertification
    from app.models.product import Market
    if not db.query(Market).filter(Market.code == code).first():
        raise HTTPException(status_code=404, detail="市场不存在")
    c = MarketCertification(
        market_code=code,
        cert_type=data["cert_type"],
        cert_standard=data["cert_standard"],
        description=data.get("description"),
        is_required=data.get("is_required", "true"),
        sort_order=data.get("sort_order", 0),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"message": "新增成功", "id": c.id}


@router.put("/markets/{code}/certifications/{cid}")
def update_market_certification(
    code: str,
    cid: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """更新认证要求"""
    from app.models.pm_config import MarketCertification
    c = db.query(MarketCertification).filter(
        MarketCertification.id == cid,
        MarketCertification.market_code == code,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="认证记录不存在")
    for key in ("cert_type", "cert_standard", "description", "is_required", "sort_order"):
        if key in data:
            setattr(c, key, data[key])
    db.commit()
    return {"message": "更新成功"}


@router.delete("/markets/{code}/certifications/{cid}")
def delete_market_certification(
    code: str,
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """删除认证要求"""
    from app.models.pm_config import MarketCertification
    c = db.query(MarketCertification).filter(
        MarketCertification.id == cid,
        MarketCertification.market_code == code,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="认证记录不存在")
    db.delete(c)
    db.commit()
    return {"message": "已删除"}


# ══════════════════════════════════════════════════
# 市场压缩机信息 CRUD
# ══════════════════════════════════════════════════

@router.get("/markets/{code}/compressors")
def list_market_compressors(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """列出指定市场的压缩机信息"""
    from app.models.pm_config import MarketCompressor
    items = db.query(MarketCompressor).filter(
        MarketCompressor.market_code == code
    ).order_by(MarketCompressor.manufacturer, MarketCompressor.model).all()
    return [
        {
            "id": c.id,
            "market_code": c.market_code,
            "manufacturer": c.manufacturer,
            "model": c.model,
            "capacity_range": c.capacity_range,
            "notes": c.notes,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in items
    ]


@router.post("/markets/{code}/compressors")
def create_market_compressor(
    code: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """新增市场压缩机信息"""
    from app.models.pm_config import MarketCompressor
    from app.models.product import Market
    if not db.query(Market).filter(Market.code == code).first():
        raise HTTPException(status_code=404, detail="市场不存在")
    c = MarketCompressor(
        market_code=code,
        manufacturer=data["manufacturer"],
        model=data.get("model"),
        capacity_range=data.get("capacity_range"),
        notes=data.get("notes"),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"message": "新增成功", "id": c.id}


@router.put("/markets/{code}/compressors/{cid}")
def update_market_compressor(
    code: str,
    cid: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """更新压缩机信息"""
    from app.models.pm_config import MarketCompressor
    c = db.query(MarketCompressor).filter(
        MarketCompressor.id == cid,
        MarketCompressor.market_code == code,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="压缩机记录不存在")
    for key in ("manufacturer", "model", "capacity_range", "notes"):
        if key in data:
            setattr(c, key, data[key])
    db.commit()
    return {"message": "更新成功"}


@router.delete("/markets/{code}/compressors/{cid}")
def delete_market_compressor(
    code: str,
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """删除压缩机信息"""
    from app.models.pm_config import MarketCompressor
    c = db.query(MarketCompressor).filter(
        MarketCompressor.id == cid,
        MarketCompressor.market_code == code,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="压缩机记录不存在")
    db.delete(c)
    db.commit()
    return {"message": "已删除"}
