"""竞品参数库 API — 竞品机型查询 & 对标分析"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
    energy_rating: Optional[str] = Field(None, max_length=40)
    cooling_w: Optional[int] = None
    heating_w: Optional[int] = None
    eer: Optional[float] = None
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
    energy_rating: Optional[str] = Field(None, max_length=40)
    cooling_w: Optional[int] = None
    heating_w: Optional[int] = None
    eer: Optional[float] = None
    noise_indoor_db: Optional[float] = None
    noise_outdoor_db: Optional[float] = None
    airflow_m3h: Optional[float] = None
    indoor_size_mm: Optional[str] = Field(None, max_length=60)
    outdoor_size_mm: Optional[str] = Field(None, max_length=60)
    factory_price: Optional[str] = Field(None, max_length=60)
    launch_year: Optional[int] = None
    notes: Optional[str] = None


# ── 序列化辅助 ────────────────────────────────────────────────────

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
    }


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


# ── 对标查询 ──────────────────────────────────────────────────────

PARAM_NAMES = [
    {"key": "cooling_w", "label": "制冷功率", "unit": "W"},
    {"key": "heating_w", "label": "制热功率", "unit": "W"},
    {"key": "eer", "label": "能效比 EER", "unit": ""},
    {"key": "noise_indoor_db", "label": "室内噪音", "unit": "dB"},
    {"key": "noise_outdoor_db", "label": "室外噪音", "unit": "dB"},
    {"key": "airflow_m3h", "label": "循环风量", "unit": "m³/h"},
    {"key": "indoor_size_mm", "label": "内机尺寸", "unit": "mm"},
    {"key": "outdoor_size_mm", "label": "外机尺寸", "unit": "mm"},
    {"key": "factory_price", "label": "出厂价", "unit": ""},
    {"key": "launch_year", "label": "上市年份", "unit": ""},
    {"key": "energy_rating", "label": "能效等级", "unit": ""},
]


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
        "param_names": PARAM_NAMES,
    }
