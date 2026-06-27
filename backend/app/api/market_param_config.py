"""市场参数配置 API — 产品经理自行配置每个市场有哪些专有参数"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.market_param_config import MarketParamConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pm/market-params", tags=["市场参数配置"])


# ── Pydantic Schemas ─────────────────────────────────────────────

class ParamConfigCreate(BaseModel):
    market_code: str = Field(..., max_length=20)
    param_key: str = Field(..., max_length=50, pattern=r"^[a-z_][a-z0-9_]*$")
    param_label: str = Field(..., max_length=100)
    param_unit: Optional[str] = Field(None, max_length=50)
    data_type: str = Field("float", pattern=r"^(float|int|string|select)$")
    sort_order: int = 0
    is_required: bool = False
    options: Optional[list] = None


class ParamConfigUpdate(BaseModel):
    param_label: Optional[str] = Field(None, max_length=100)
    param_unit: Optional[str] = Field(None, max_length=50)
    data_type: Optional[str] = Field(None, pattern=r"^(float|int|string|select)$")
    sort_order: Optional[int] = None
    is_required: Optional[bool] = None
    options: Optional[list] = None
    is_active: Optional[bool] = None


# ── 列出市场的参数配置 ────────────────────────────────────────────

@router.get("/{market_code}")
def list_param_configs(
    market_code: str,
    only_active: bool = Query(True, description="只返回激活的配置"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """列出指定市场的参数配置"""
    q = db.query(MarketParamConfig).filter(
        MarketParamConfig.market_code == market_code
    )
    if only_active:
        q = q.filter(MarketParamConfig.is_active == "true")
    items = q.order_by(MarketParamConfig.sort_order, MarketParamConfig.param_key).all()
    return [_serialize_config(c) for c in items]


@router.get("/{market_code}/{param_key}")
def get_param_config(
    market_code: str,
    param_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取单条参数配置"""
    c = db.query(MarketParamConfig).filter(
        MarketParamConfig.market_code == market_code,
        MarketParamConfig.param_key == param_key,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="参数配置不存在")
    return _serialize_config(c)


# ── 写入 ──────────────────────────────────────────────────────────

@router.post("")
def create_param_config(
    data: ParamConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """新增参数配置"""
    existing = db.query(MarketParamConfig).filter(
        MarketParamConfig.market_code == data.market_code,
        MarketParamConfig.param_key == data.param_key,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"参数 '{data.param_key}' 已存在")
    c = MarketParamConfig(
        market_code=data.market_code,
        param_key=data.param_key,
        param_label=data.param_label,
        param_unit=data.param_unit,
        data_type=data.data_type,
        sort_order=data.sort_order,
        is_required="true" if data.is_required else "false",
        options=data.options,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _serialize_config(c)


@router.put("/{market_code}/{param_key}")
def update_param_config(
    market_code: str,
    param_key: str,
    data: ParamConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """更新参数配置"""
    c = db.query(MarketParamConfig).filter(
        MarketParamConfig.market_code == market_code,
        MarketParamConfig.param_key == param_key,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="参数配置不存在")
    if data.param_label is not None:
        c.param_label = data.param_label
    if data.param_unit is not None:
        c.param_unit = data.param_unit
    if data.data_type is not None:
        c.data_type = data.data_type
    if data.sort_order is not None:
        c.sort_order = data.sort_order
    if data.is_required is not None:
        c.is_required = "true" if data.is_required else "false"
    if data.options is not None:
        c.options = data.options
    if data.is_active is not None:
        c.is_active = "true" if data.is_active else "false"
    db.commit()
    db.refresh(c)
    return _serialize_config(c)


@router.delete("/{market_code}/{param_key}")
def delete_param_config(
    market_code: str,
    param_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """删除参数配置"""
    c = db.query(MarketParamConfig).filter(
        MarketParamConfig.market_code == market_code,
        MarketParamConfig.param_key == param_key,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="参数配置不存在")
    db.delete(c)
    db.commit()
    return {"message": "已删除"}


# ── 序列化 ──────────────────────────────────────────────────────

def _serialize_config(c: MarketParamConfig) -> dict:
    return {
        "id": c.id,
        "market_code": c.market_code,
        "param_key": c.param_key,
        "param_label": c.param_label,
        "param_unit": c.param_unit or "",
        "data_type": c.data_type,
        "sort_order": c.sort_order,
        "is_required": c.is_required == "true",
        "options": c.options,
        "is_active": c.is_active == "true",
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
