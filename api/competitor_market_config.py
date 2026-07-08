"""竞品市场配置 API — 市场认证要求 & 压缩机信息 CRUD"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pm", tags=["竞品库-市场配置"])


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
