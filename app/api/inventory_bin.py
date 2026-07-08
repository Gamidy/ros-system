"""库位管理 API: 库位CRUD + 统计 + 查询"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.inventory import Warehouse, StorageLocation
from app.schemas.inventory import (
    StorageLocationCreate, StorageLocationUpdate, StorageLocationOut, LocationStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory/locations", tags=["库位管理"])


@router.get("", response_model=dict)
def list_locations(
    warehouse_id: Optional[int] = Query(None),
    zone: Optional[str] = Query(None),
    location_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="搜索编码/名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """查询库位列表"""
    q = db.query(StorageLocation).filter(StorageLocation.is_deleted == 0)
    if warehouse_id:
        q = q.filter(StorageLocation.warehouse_id == warehouse_id)
    if zone:
        q = q.filter(StorageLocation.zone == zone)
    if location_type:
        q = q.filter(StorageLocation.location_type == location_type)
    if status:
        q = q.filter(StorageLocation.status == status)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            StorageLocation.code.like(like) | StorageLocation.name.like(like)
        )

    total = q.count()
    items = q.order_by(StorageLocation.sort_order, StorageLocation.code).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []
    for loc in items:
        result.append({
            "id": loc.id,
            "warehouse_id": loc.warehouse_id,
            "warehouse_name": loc.warehouse.name if loc.warehouse else None,
            "code": loc.code,
            "name": loc.name,
            "zone": loc.zone,
            "row_label": loc.row_label,
            "shelf": loc.shelf,
            "bin": loc.bin,
            "max_capacity": loc.max_capacity,
            "current_occupied": loc.current_occupied,
            "capacity_unit": loc.capacity_unit,
            "location_type": loc.location_type,
            "is_lockable": loc.is_lockable,
            "status": loc.status,
            "sort_order": loc.sort_order,
            "remark": loc.remark,
            "usage_rate": round(loc.current_occupied / loc.max_capacity * 100, 1) if loc.max_capacity > 0 else 0,
            "created_at": loc.created_at.isoformat() if loc.created_at else None,
            "updated_at": loc.updated_at.isoformat() if loc.updated_at else None,
        })

    return {"total": total, "items": result, "page": page, "page_size": page_size}


@router.post("", response_model=StorageLocationOut, status_code=201)
def create_location(
    data: StorageLocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """创建库位"""
    # 检查仓库
    wh = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id, Warehouse.is_deleted == 0).first()
    if not wh:
        raise HTTPException(404, "仓库不存在")
    # 检查编码唯一
    exist = db.query(StorageLocation).filter(
        StorageLocation.warehouse_id == data.warehouse_id,
        StorageLocation.code == data.code,
        StorageLocation.is_deleted == 0,
    ).first()
    if exist:
        raise HTTPException(400, f"库位编码 {data.code} 在该仓库中已存在")

    loc = StorageLocation(**data.model_dump())
    db.add(loc)
    db.flush()
    db.commit()
    db.refresh(loc)
    return loc


@router.get("/{lid}", response_model=StorageLocationOut)
def get_location(
    lid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """获取库位详情"""
    loc = db.query(StorageLocation).filter(StorageLocation.id == lid, StorageLocation.is_deleted == 0).first()
    if not loc:
        raise HTTPException(404, "库位不存在")
    return loc


@router.put("/{lid}", response_model=StorageLocationOut)
def update_location(
    lid: int,
    data: StorageLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """更新库位"""
    loc = db.query(StorageLocation).filter(StorageLocation.id == lid, StorageLocation.is_deleted == 0).first()
    if not loc:
        raise HTTPException(404, "库位不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(loc, k, v)
    db.flush()
    db.commit()
    db.refresh(loc)
    return loc


@router.delete("/{lid}")
def delete_location(
    lid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """软删除库位"""
    loc = db.query(StorageLocation).filter(StorageLocation.id == lid, StorageLocation.is_deleted == 0).first()
    if not loc:
        raise HTTPException(404, "库位不存在")
    if loc.current_occupied > 0:
        raise HTTPException(400, "库位非空，无法删除")
    loc.is_deleted = 1
    db.commit()
    return {"message": "库位已删除"}


@router.patch("/{lid}/occupy")
def update_occupancy(
    lid: int,
    qty: float = Query(..., description="新的占用量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """更新库位占用量（上架/下架时调用）"""
    loc = db.query(StorageLocation).filter(StorageLocation.id == lid, StorageLocation.is_deleted == 0).first()
    if not loc:
        raise HTTPException(404, "库位不存在")
    if qty < 0:
        raise HTTPException(400, "占用量不能为负")
    if loc.max_capacity > 0 and qty > loc.max_capacity:
        raise HTTPException(400, f"占用量超过最大容量 {loc.max_capacity}{loc.capacity_unit}")
    old_qty = loc.current_occupied
    loc.current_occupied = qty
    # 自动更新状态
    if loc.max_capacity > 0 and qty >= loc.max_capacity:
        loc.status = "full"
    elif loc.status == "full" and qty < loc.max_capacity:
        loc.status = "active"
    db.commit()
    return {"message": "占用量已更新", "old_qty": old_qty, "new_qty": qty}


@router.get("/stats/overview", response_model=LocationStatsOut)
def location_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """库位统计概览"""
    total = db.query(StorageLocation).filter(StorageLocation.is_deleted == 0).count()
    active = db.query(StorageLocation).filter(
        StorageLocation.is_deleted == 0, StorageLocation.status == "active"
    ).count()
    full = db.query(StorageLocation).filter(
        StorageLocation.is_deleted == 0, StorageLocation.status == "full"
    ).count()
    blocked = db.query(StorageLocation).filter(
        StorageLocation.is_deleted == 0,
        StorageLocation.status.in_(["blocked", "maintenance", "inactive"]),
    ).count()

    # 按类型统计
    type_rows = db.query(
        StorageLocation.location_type, func.count(StorageLocation.id)
    ).filter(StorageLocation.is_deleted == 0).group_by(StorageLocation.location_type).all()
    by_type = {row[0]: row[1] for row in type_rows}

    # 综合利用率
    total_cap = db.query(func.coalesce(func.sum(StorageLocation.max_capacity), 0)).filter(
        StorageLocation.is_deleted == 0, StorageLocation.max_capacity > 0
    ).scalar() or 0
    total_occ = db.query(func.coalesce(func.sum(StorageLocation.current_occupied), 0)).filter(
        StorageLocation.is_deleted == 0, StorageLocation.max_capacity > 0
    ).scalar() or 0
    usage_rate = round(total_occ / total_cap * 100, 1) if total_cap > 0 else 0

    return LocationStatsOut(
        total_locations=total,
        active_count=active,
        full_count=full,
        blocked_count=blocked,
        usage_rate=usage_rate,
        by_type=by_type,
    )
