"""库存管理 API: 仓库CRUD + 库存台账 + 库存调整 + 流水 + 统计"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.inventory import Warehouse, Inventory, InventoryTransaction
from app.schemas.inventory import (
    WarehouseCreate, WarehouseOut, WarehouseUpdate,
    InventoryOut, InventoryAdjust,
    InventoryStatsOut,
    InventoryTransactionOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["库存管理"])


# ══════════════════════════════════════════════════
# 仓库管理
# ══════════════════════════════════════════════════


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(
    status: Optional[str] = Query(None, description="筛选状态"),
    search: Optional[str] = Query(None, description="搜索名称/编码"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """获取仓库列表"""
    q = db.query(Warehouse).filter(Warehouse.is_deleted == 0)
    if status:
        q = q.filter(Warehouse.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Warehouse.name.like(like), Warehouse.code.like(like)))
    return q.order_by(Warehouse.code).all()


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """创建仓库"""
    exist = db.query(Warehouse).filter(Warehouse.code == data.code, Warehouse.is_deleted == 0).first()
    if exist:
        raise HTTPException(400, f"仓库编码 {data.code} 已存在")
    wh = Warehouse(**data.model_dump())
    db.add(wh)
    db.flush()
    db.commit()
    db.refresh(wh)
    logger.info("仓库创建: id=%d code=%s by=%s", wh.id, wh.code, current_user.username)
    return wh


@router.get("/warehouses/{wh_id}", response_model=WarehouseOut)
def get_warehouse(
    wh_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """获取仓库详情"""
    wh = db.query(Warehouse).filter(Warehouse.id == wh_id, Warehouse.is_deleted == 0).first()
    if not wh:
        raise HTTPException(404, "仓库不存在")
    return wh


@router.put("/warehouses/{wh_id}", response_model=WarehouseOut)
def update_warehouse(
    wh_id: int,
    data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """更新仓库"""
    wh = db.query(Warehouse).filter(Warehouse.id == wh_id, Warehouse.is_deleted == 0).first()
    if not wh:
        raise HTTPException(404, "仓库不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(wh, k, v)
    db.flush()
    db.commit()
    db.refresh(wh)
    return wh


@router.delete("/warehouses/{wh_id}")
def delete_warehouse(
    wh_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """软删除仓库"""
    wh = db.query(Warehouse).filter(Warehouse.id == wh_id, Warehouse.is_deleted == 0).first()
    if not wh:
        raise HTTPException(404, "仓库不存在")
    # 检查是否有库存
    has_stock = db.query(Inventory).filter(Inventory.warehouse_id == wh_id).first()
    if has_stock:
        raise HTTPException(400, "该仓库存在库存记录，无法删除")
    wh.is_deleted = 1
    db.flush()
    db.commit()
    return {"message": "仓库已删除"}


# ══════════════════════════════════════════════════
# 库存台账
# ══════════════════════════════════════════════════


@router.get("/items", response_model=dict)
def list_inventory(
    warehouse_id: Optional[int] = Query(None, description="仓库ID"),
    part_no: Optional[str] = Query(None, description="物料编码"),
    part_name: Optional[str] = Query(None, description="物料名称"),
    low_stock: Optional[bool] = Query(None, description="仅低库存"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """查询库存台账（分页+筛选）"""
    q = db.query(Inventory)
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    if part_no:
        q = q.filter(Inventory.part_no.like(f"%{part_no}%"))
    if part_name:
        q = q.filter(Inventory.part_name.like(f"%{part_name}%"))
    if low_stock:
        q = q.filter(Inventory.qty <= Inventory.min_stock, Inventory.min_stock > 0)

    total = q.count()
    items = q.order_by(Inventory.part_no, Inventory.warehouse_id).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []
    for inv in items:
        d = {
            "id": inv.id,
            "warehouse_id": inv.warehouse_id,
            "warehouse_name": inv.warehouse.name if inv.warehouse else None,
            "part_no": inv.part_no,
            "part_name": inv.part_name,
            "spec": inv.spec,
            "unit": inv.unit,
            "qty": inv.qty,
            "available_qty": inv.available_qty,
            "locked_qty": inv.locked_qty,
            "min_stock": inv.min_stock,
            "max_stock": inv.max_stock,
            "reorder_point": inv.reorder_point,
            "unit_cost": inv.unit_cost,
            "total_value": inv.total_value,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        }
        result.append(d)
    return {"total": total, "items": result, "page": page, "page_size": page_size}


@router.get("/items/stats", response_model=InventoryStatsOut)
def inventory_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """库存统计概览"""
    # 总物料数
    total_part = db.query(func.count(Inventory.id)).scalar() or 0
    # 总库存量
    total_qty = db.query(func.coalesce(func.sum(Inventory.qty), 0)).scalar()
    # 总库存金额
    total_val = db.query(func.coalesce(func.sum(Inventory.total_value), 0)).scalar()
    # 低库存物料
    low_items = db.query(Inventory).filter(
        Inventory.qty <= Inventory.min_stock,
        Inventory.min_stock > 0,
    ).all()
    # 仓库数
    wh_count = db.query(Warehouse).filter(Warehouse.is_deleted == 0).count()

    low_list = []
    for inv in low_items:
        low_list.append({
            "id": inv.id,
            "warehouse_id": inv.warehouse_id,
            "warehouse_name": inv.warehouse.name if inv.warehouse else None,
            "part_no": inv.part_no,
            "part_name": inv.part_name,
            "spec": inv.spec,
            "unit": inv.unit,
            "qty": inv.qty,
            "available_qty": inv.available_qty,
            "locked_qty": inv.locked_qty,
            "min_stock": inv.min_stock,
            "max_stock": inv.max_stock,
            "reorder_point": inv.reorder_point,
            "unit_cost": inv.unit_cost,
            "total_value": inv.total_value,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        })

    return InventoryStatsOut(
        total_part_count=total_part,
        total_qty=float(total_qty),
        total_value=float(total_val),
        low_stock_count=len(low_items),
        warehouse_count=wh_count,
        low_stock_items=low_list,
    )


@router.post("/items/adjust", response_model=dict)
def adjust_inventory(
    data: InventoryAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """库存调整（入库/出库/手动调整）

    自动创建/更新库存台账 + 记录流水。
    """
    # 查找或创建库存记录
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == data.warehouse_id,
        Inventory.part_no == data.part_no,
    ).first()

    is_new = False
    if not inv:
        inv = Inventory(
            warehouse_id=data.warehouse_id,
            part_no=data.part_no,
            part_name=data.part_name or data.part_no,
            spec=data.spec,
            unit=data.unit,
            qty=0,
            available_qty=0,
            locked_qty=0,
            unit_cost=data.unit_cost or 0,
        )
        db.add(inv)
        db.flush()
        is_new = True

    # 计算变动
    change_qty = data.qty
    if data.trans_type == "out":
        change_qty = -data.qty
    elif data.trans_type == "adjust":
        # adjust: 直接设置新数量
        old_qty = inv.qty
        change_qty = data.qty - old_qty

    if change_qty == 0:
        raise HTTPException(400, "变动量为0，无需调整")

    balance_before = inv.qty
    inv.qty += change_qty
    if inv.qty < 0:
        raise HTTPException(400, f"库存不足。当前库存 {balance_before}，尝试出库 {data.qty}")
    inv.available_qty = max(0, inv.qty - inv.locked_qty)

    # 更新成本价
    if data.unit_cost is not None:
        inv.unit_cost = data.unit_cost
    # 更新库存参数
    if data.set_min_stock is not None:
        inv.min_stock = data.set_min_stock
    if data.set_max_stock is not None:
        inv.max_stock = data.set_max_stock
    if data.set_reorder_point is not None:
        inv.reorder_point = data.set_reorder_point
    # 更新金额
    inv.total_value = inv.qty * inv.unit_cost

    # 记录流水
    txn = InventoryTransaction(
        warehouse_id=data.warehouse_id,
        part_no=inv.part_no,
        part_name=inv.part_name,
        spec=inv.spec,
        unit=inv.unit,
        trans_type=data.trans_type,
        qty=change_qty,
        balance_before=balance_before,
        balance_after=inv.qty,
        ref_doc_type=data.ref_doc_type,
        ref_doc_id=data.ref_doc_id,
        ref_doc_no=data.ref_doc_no,
        operator=data.operator or current_user.username,
        remark=data.remark,
    )
    db.add(txn)
    db.flush()
    db.commit()

    logger.info(
        "库存调整: part=%s wh=%d type=%s qty=%+.1f before=%.1f after=%.1f by=%s",
        data.part_no, data.warehouse_id, data.trans_type,
        change_qty, balance_before, inv.qty, current_user.username,
    )

    return {
        "message": "库存调整成功",
        "inventory_id": inv.id,
        "transaction_id": txn.id,
        "balance_before": balance_before,
        "balance_after": inv.qty,
        "change_qty": change_qty,
    }


# ══════════════════════════════════════════════════
# 库存流水
# ══════════════════════════════════════════════════


@router.get("/transactions", response_model=dict)
def list_transactions(
    warehouse_id: Optional[int] = Query(None, description="仓库ID"),
    part_no: Optional[str] = Query(None, description="物料编码"),
    trans_type: Optional[str] = Query(None, description="in/out/adjust"),
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """查询库存流水（分页+筛选）"""
    q = db.query(InventoryTransaction)
    if warehouse_id:
        q = q.filter(InventoryTransaction.warehouse_id == warehouse_id)
    if part_no:
        q = q.filter(InventoryTransaction.part_no.like(f"%{part_no}%"))
    if trans_type:
        q = q.filter(InventoryTransaction.trans_type == trans_type)
    if date_from:
        q = q.filter(InventoryTransaction.created_at >= date_from)
    if date_to:
        q = q.filter(InventoryTransaction.created_at <= f"{date_to} 23:59:59")

    total = q.count()
    txns = q.order_by(InventoryTransaction.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []
    for t in txns:
        wh_name = None
        wh = db.query(Warehouse).filter(Warehouse.id == t.warehouse_id).first()
        if wh:
            wh_name = wh.name
        result.append({
            "id": t.id,
            "warehouse_id": t.warehouse_id,
            "warehouse_name": wh_name,
            "part_no": t.part_no,
            "part_name": t.part_name,
            "spec": t.spec,
            "unit": t.unit,
            "trans_type": t.trans_type,
            "qty": t.qty,
            "balance_before": t.balance_before,
            "balance_after": t.balance_after,
            "ref_doc_type": t.ref_doc_type,
            "ref_doc_id": t.ref_doc_id,
            "ref_doc_no": t.ref_doc_no,
            "operator": t.operator,
            "remark": t.remark,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {"total": total, "items": result, "page": page, "page_size": page_size}


# ══════════════════════════════════════════════════
# 集成辅助: 来料检验合格→自动入库
# ══════════════════════════════════════════════════


def auto_stock_in(
    db: Session,
    warehouse_id: int,
    part_no: str,
    part_name: str,
    spec: str,
    unit: str,
    qty: float,
    unit_cost: float,
    ref_doc_type: str,
    ref_doc_id: int,
    ref_doc_no: str,
    operator: str,
) -> dict:
    """来料检验合格后自动入库（供 purchases.py 调用）"""
    # 查找或创建库存记录
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id,
        Inventory.part_no == part_no,
    ).first()
    if not inv:
        inv = Inventory(
            warehouse_id=warehouse_id,
            part_no=part_no,
            part_name=part_name,
            spec=spec,
            unit=unit,
            qty=0,
            available_qty=0,
            locked_qty=0,
            unit_cost=unit_cost or 0,
        )
        db.add(inv)
        db.flush()

    balance_before = inv.qty
    inv.qty += qty
    inv.available_qty = max(0, inv.qty - inv.locked_qty)
    if unit_cost > 0:
        inv.unit_cost = unit_cost
    inv.total_value = inv.qty * inv.unit_cost

    txn = InventoryTransaction(
        warehouse_id=warehouse_id,
        part_no=inv.part_no,
        part_name=inv.part_name,
        spec=spec,
        unit=unit,
        trans_type="in",
        qty=qty,
        balance_before=balance_before,
        balance_after=inv.qty,
        ref_doc_type=ref_doc_type,
        ref_doc_id=ref_doc_id,
        ref_doc_no=ref_doc_no,
        operator=operator,
        remark=f"来料检验合格自动入库[{ref_doc_no}]",
    )
    db.add(txn)
    db.flush()
    return {"inventory_id": inv.id, "transaction_id": txn.id, "balance_after": inv.qty}
