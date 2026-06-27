"""竞品对标查询 API — 独立路由，无认证依赖"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.competitor import CompetitorModel

router = APIRouter(prefix="/pm", tags=["竞品对标"])

PARAM_NAMES = [
    {"key": "cooling_w", "label": "制冷功率", "unit": "W"},
    {"key": "heating_w", "label": "制热功率", "unit": "W"},
    {"key": "eer", "label": "能效比 EER", "unit": ""},
    {"key": "cspf", "label": "CSPF 能效", "unit": ""},
    {"key": "noise_indoor_db", "label": "室内噪音", "unit": "dB"},
    {"key": "noise_outdoor_db", "label": "室外噪音", "unit": "dB"},
    {"key": "airflow_m3h", "label": "循环风量", "unit": "m³/h"},
    {"key": "indoor_size_mm", "label": "内机尺寸", "unit": "mm"},
    {"key": "outdoor_size_mm", "label": "外机尺寸", "unit": "mm"},
    {"key": "factory_price", "label": "出厂价", "unit": ""},
    {"key": "launch_year", "label": "上市年份", "unit": ""},
    {"key": "energy_rating", "label": "能效等级", "unit": ""},
]


def _serialize(item: CompetitorModel) -> dict:
    return {
        "id": item.id,
        "brand": item.brand,
        "model": item.model,
        "market": item.market,
        "product_type": item.product_type,
        "cooling_capacity": item.cooling_capacity,
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


@router.get("/competitors/benchmark")
def benchmark_competitors(
    market: str = Query(..., description="目标市场（必填），如'越南'"),
    db: Session = Depends(get_db),
) -> dict:
    """对标查询：返回指定市场下所有竞品的对比数据（无需登录）"""
    items = (
        db.query(CompetitorModel)
        .filter(CompetitorModel.market == market)
        .order_by(CompetitorModel.brand, CompetitorModel.model)
        .all()
    )
    return {
        "market": market,
        "competitors": [_serialize(it) for it in items],
        "param_names": PARAM_NAMES,
    }
