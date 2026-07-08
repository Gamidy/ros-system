"""竞品对标 API — 对标分析 + 从对标生成产品策划"""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.competitor import CompetitorModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pm", tags=["竞品对标"])


# ── 字段完整性校验 ────────────────────────────────────────────────

REQUIRED_FIELDS = [
    "brand", "model", "market", "product_type", "cooling_capacity",
    "cooling_capacity_w", "heating_capacity_w",
    "energy_rating", "cooling_w", "heating_w",
    "noise_indoor_db", "noise_outdoor_db", "airflow_m3h",
    "indoor_size_mm", "outdoor_size_mm", "factory_price", "launch_year",
]


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


# 市场能效标准
MARKET_ENERGY_STANDARDS_FALLBACK = {
    "越南":       {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "印度尼西亚": {"param_key": "cspf",  "label": "CSPF",  "unit": "W/W",    "type": "seasonal"},
    "马来西亚":   {"param_key": "cspf",  "label": "APF",   "unit": "W/W",    "type": "seasonal"},
    "沙特":     {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "阿联酋":   {"param_key": "seer",  "label": "SEER",  "unit": "BTU/Wh", "type": "seasonal"},
    "美国":     {"param_key": "seer",  "label": "SEER2", "unit": "BTU/Wh", "type": "seasonal"},
    "欧盟":     {"param_key": "seer",  "label": "SEER",  "unit": "W/W",    "type": "seasonal"},
}


def get_energy_param_key(market: str) -> str:
    std = MARKET_ENERGY_STANDARDS_FALLBACK.get(market)
    return std["param_key"] if std else "eer"


def get_energy_param_label(market: str) -> str:
    std = MARKET_ENERGY_STANDARDS_FALLBACK.get(market)
    return std["label"] if std else "EER"


def check_competitor_completeness(item: CompetitorModel) -> dict:
    """检查单条竞品数据的完整性"""
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
    key = get_energy_param_key(market)
    return getattr(item, key, None)


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


def get_param_names(market: str) -> list:
    """根据市场返回完整参数列表"""
    params = list(BASE_PARAM_NAMES)
    energy_label = get_energy_param_label(market)
    params.append({
        "key": get_energy_param_key(market),
        "label": energy_label,
        "unit": "W/W" if energy_label in ("CSPF", "ISEER", "SEER") else "",
    })
    return params


def _serialize(item: CompetitorModel) -> dict:
    """序列化竞品数据"""
    completeness = check_competitor_completeness(item)
    eff_value = get_efficiency_value(item, item.market)
    energy_label = get_energy_param_label(item.market)
    extra = item.extra_fields or {}
    if isinstance(extra, str):
        try:
            import json
            extra = json.loads(extra)
        except (json.JSONDecodeError, TypeError):
            extra = {}
    return {
        "id": item.id, "brand": item.brand, "model": item.model,
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
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "efficiency_value": eff_value,
        "efficiency_label": energy_label,
        "efficiency_key": get_energy_param_key(item.market),
        "is_complete": completeness["is_complete"],
        "missing_fields": completeness["missing_fields"],
    }


# ══════════════════════════════════════════════════
# 对标查询
# ══════════════════════════════════════════════════

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
# 完整性校验
# ══════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════
# 从竞品对标生成产品策划
# ══════════════════════════════════════════════════

class CreatePlanFromBenchmark(BaseModel):
    market: str = Field(..., description="目标市场")
    targets: dict[str, float | str | None] = Field(..., description="采纳的目标参数 {param_key: value}")
    competitor_sources: Optional[dict[str, dict]] = Field(None, description="参数来源 {param_key: {brand, model, value}}")


@router.post("/create-plan-from-benchmark", status_code=201)
def create_plan_from_benchmark(
    data: CreatePlanFromBenchmark,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """从竞品对标数据生成产品策划书"""
    from app.services.product_plan_workflow import create_product_plan as workflow_create
    from app.models.product_plan_subs import ProductPlanTechSpec

    # 1. 生成策划名称
    name = f"{data.market}新品-{datetime.now().strftime('%Y%m%d')}"

    # 2. 构建性能参数JSON
    core_perf = {}
    for key, val in data.targets.items():
        if val is not None:
            core_perf[key] = val

    if data.competitor_sources:
        core_perf["_sources"] = data.competitor_sources
    core_perf["_market"] = data.market
    core_perf["_generated_at"] = datetime.now().isoformat()

    # 3. 创建策划
    plan_data = {
        "name": name,
        "market": data.market,
        "performance_target": json.dumps(core_perf, ensure_ascii=False),
    }
    try:
        plan = workflow_create(db, plan_data, current_user.username)

        # 4. 创建技术要求（core_performance）
        if not db.query(ProductPlanTechSpec).filter(
            ProductPlanTechSpec.product_plan_id == plan.id
        ).first():
            tech_spec = ProductPlanTechSpec(
                product_plan_id=plan.id,
                core_performance=json.dumps(core_perf, ensure_ascii=False),
            )
            db.add(tech_spec)
            db.commit()

        # 5. 广播仪表盘刷新
        from app.services.ws_push import trigger_dashboard_refresh_sync
        trigger_dashboard_refresh_sync()

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "message": "策划已生成，请在「产品策划」页面继续完善",
            "params_count": len(core_perf),
        }
    except Exception as e:
        db.rollback()
        logger.exception("从竞品对标生成策划失败")
        raise HTTPException(status_code=500, detail=f"生成策划失败: {str(e)}")
