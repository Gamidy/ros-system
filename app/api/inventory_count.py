"""盘点管理 API: 盘点计划CRUD + 录入实盘 + 差异处理 + 统计"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.inventory import Inventory, InventoryTransaction
from app.models.inventory_count import InventoryCount, InventoryCountItem
from app.schemas.inventory_count import (
    InventoryCountCreate, InventoryCountOut, InventoryCountListItem,
    CountItemUpdate, CountStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory/counts", tags=["盘点管理"])


def _generate_count_no(db: Session) -> str:
    """生成盘点单号 PD-YYYYMMDD-XXXX"""
    from datetime import date
    today = date.today()
    prefix = f"PD-{today.strftime('%Y%m%d')}-"
    last = db.query(InventoryCount).filter(
        InventoryCount.count_no.like(f"{prefix}%"),
    ).order_by(InventoryCount.id.desc()).first()
    seq = 1
    if last:
        try:
            seq = int(last.count_no[-4:]) + 1
        except (ValueError, IndexError):
            seq = 1
    return f"{prefix}{seq:04d}"


# ══════════════════════════════════════════════════
# 盘点计划 CRUD
# ══════════════════════════════════════════════════


@router.get("", response_model=dict)
def list_counts(
    status: Optional[str] = Query(None, description="筛选状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """盘点计划列表"""
    q = db.query(InventoryCount)
    if status:
        q = q.filter(InventoryCount.status == status)
    total = q.count()
    items = q.order_by(InventoryCount.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []
    for c in items:
        wh_name = c.warehouse_name
        result.append({
            "id": c.id, "count_no": c.count_no,
            "warehouse_name": wh_name,
            "count_type": c.count_type, "status": c.status,
            "total_items": c.total_items, "matched_count": c.matched_count,
            "discrepancy_count": c.discrepancy_count,
            "total_discrepancy_value": c.total_discrepancy_value,
            "count_date": c.count_date.isoformat() if c.count_date else None,
            "counted_by": c.counted_by, "created_by": c.created_by,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return {"total": total, "items": result, "page": page, "page_size": page_size}


@router.post("", response_model=InventoryCountOut, status_code=201)
def create_count(
    data: InventoryCountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """创建盘点计划"""
    from app.models.inventory import Warehouse
    wh = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first()
    if not wh:
        raise HTTPException(404, "仓库不存在")

    count_no = _generate_count_no(db)
    count = InventoryCount(
        count_no=count_no,
        warehouse_id=data.warehouse_id,
        warehouse_name=wh.name,
        count_type=data.count_type,
        status="draft",
        counted_by=data.counted_by,
        remark=data.remark,
        created_by=current_user.username,
    )
    db.add(count)
    db.flush()

    # 创建盘点明细
    for item_data in data.items:
        inv = db.query(Inventory).filter(
            Inventory.id == item_data.inventory_id,
        ).first() if item_data.inventory_id else None

        sys_qty = inv.qty if inv else 0
        unit_cost = inv.unit_cost if inv else 0
        diff_qty = item_data.actual_qty - sys_qty

        item = InventoryCountItem(
            count_id=count.id,
            inventory_id=item_data.inventory_id,
            part_no=item_data.part_no,
            part_name=item_data.part_name or (inv.part_name if inv else item_data.part_no),
            spec=item_data.spec or (inv.spec if inv else None),
            unit=item_data.unit,
            system_qty=sys_qty,
            actual_qty=item_data.actual_qty,
            diff_qty=diff_qty,
            unit_cost=unit_cost,
            diff_value=diff_qty * unit_cost,
            status="matched" if diff_qty == 0 else "discrepancy",
            remark=item_data.remark,
        )
        db.add(item)

    db.flush()
    _update_count_aggregates(db, count.id)
    db.commit()
    db.refresh(count)
    logger.info("盘点计划创建: no=%s wh=%s by=%s", count_no, wh.name, current_user.username)
    return count


@router.get("/{cid}", response_model=InventoryCountOut)
def get_count(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """获取盘点详情"""
    count = db.query(InventoryCount).filter(InventoryCount.id == cid).first()
    if not count:
        raise HTTPException(404, "盘点计划不存在")
    return count


@router.put("/{cid}/items/{item_id}", response_model=dict)
def update_count_item(
    cid: int, item_id: int,
    data: CountItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """更新盘点明细（录入实盘数量）"""
    item = db.query(InventoryCountItem).filter(
        InventoryCountItem.id == item_id,
        InventoryCountItem.count_id == cid,
    ).first()
    if not item:
        raise HTTPException(404, "盘点明细不存在")

    item.actual_qty = data.actual_qty
    item.diff_qty = data.actual_qty - item.system_qty
    item.diff_value = item.diff_qty * item.unit_cost
    item.status = "matched" if item.diff_qty == 0 else "discrepancy"
    if data.remark is not None:
        item.remark = data.remark

    db.flush()
    _update_count_aggregates(db, cid)
    db.commit()
    return {"message": "实盘数量已更新", "diff_qty": item.diff_qty, "status": item.status}


@router.post("/{cid}/submit", response_model=dict)
def submit_count(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """提交盘点 — 状态转为 pending（等待审核）"""
    count = db.query(InventoryCount).filter(InventoryCount.id == cid).first()
    if not count:
        raise HTTPException(404, "盘点计划不存在")
    if count.status != "draft":
        raise HTTPException(400, f"当前状态({count.status})不可提交")
    count.status = "pending"
    db.flush()
    db.commit()
    return {"message": "盘点已提交", "status": "pending"}


@router.post("/{cid}/complete", response_model=dict)
def complete_count(
    cid: int,
    auto_adjust: bool = Query(True, description="是否自动调整差异库存"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """完成盘点 — 可选自动调账"""
    count = db.query(InventoryCount).filter(InventoryCount.id == cid).first()
    if not count:
        raise HTTPException(404, "盘点计划不存在")
    if count.status not in ("pending", "in_progress"):
        raise HTTPException(400, f"当前状态({count.status})不可完成")

    if auto_adjust:
        adjusted = 0
        for item in count.items:
            if item.status == "discrepancy" and item.diff_qty != 0:
                # 更新库存
                inv = db.query(Inventory).filter(
                    Inventory.id == item.inventory_id,
                ).first() if item.inventory_id else None

                if inv:
                    old_qty = inv.qty
                    inv.qty += item.diff_qty
                    inv.available_qty = max(0, inv.qty - inv.locked_qty)
                    inv.total_value = inv.qty * inv.unit_cost

                    # 记录流水
                    txn = InventoryTransaction(
                        warehouse_id=count.warehouse_id,
                        part_no=item.part_no,
                        part_name=item.part_name,
                        spec=item.spec,
                        unit=item.unit,
                        trans_type="adjust",
                        qty=item.diff_qty,
                        balance_before=old_qty,
                        balance_after=inv.qty,
                        ref_doc_type="inventory_count",
                        ref_doc_id=count.id,
                        ref_doc_no=count.count_no,
                        operator=current_user.username,
                        remark=f"盘点调账[{count.count_no}]: 系统{item.system_qty}→实盘{item.actual_qty}",
                    )
                    db.add(txn)
                    item.status = "adjusted"
                    item.adjusted_at = datetime.now()
                    adjusted += 1

        count.matched_count = len([i for i in count.items if i.status == "matched"])
        count.discrepancy_count = len([i for i in count.items if i.status in ("discrepancy", "adjusted") and i.diff_qty != 0])

    count.status = "completed"
    db.flush()
    db.commit()
    return {
        "message": "盘点已完成",
        "status": "completed",
        "total_items": count.total_items,
        "discrepancy_count": count.discrepancy_count,
        "total_discrepancy_value": count.total_discrepancy_value,
        "adjusted_items": adjusted if auto_adjust else 0,
    }


@router.delete("/{cid}")
def delete_count(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """删除盘点计划（仅draft状态）"""
    count = db.query(InventoryCount).filter(InventoryCount.id == cid).first()
    if not count:
        raise HTTPException(404, "盘点计划不存在")
    if count.status != "draft":
        raise HTTPException(400, f"当前状态({count.status})不可删除")
    db.delete(count)
    db.commit()
    return {"message": "盘点计划已删除"}


# ══════════════════════════════════════════════════
# 统计
# ══════════════════════════════════════════════════


@router.get("/stats/overview", response_model=CountStatsOut)
def count_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """盘点统计概览"""
    total = db.query(InventoryCount).count()
    pending = db.query(InventoryCount).filter(InventoryCount.status.in_(["draft", "pending"])).count()
    completed = db.query(InventoryCount).filter(InventoryCount.status == "completed").count()
    # 有差异的盘点数
    discrepancy = db.query(InventoryCount).filter(
        InventoryCount.discrepancy_count > 0,
    ).count()
    # 总差异金额（所有已完成盘点）
    total_dv = db.query(
        func.coalesce(func.sum(InventoryCount.total_discrepancy_value), 0),
    ).filter(
        InventoryCount.status == "completed",
    ).scalar()

    return CountStatsOut(
        total_counts=total,
        pending_count=pending,
        completed_count=completed,
        discrepancy_count=discrepancy,
        total_discrepancy_value=float(total_dv),
    )


def _update_count_aggregates(db: Session, count_id: int):
    """更新盘点计划的聚合数据"""
    count = db.query(InventoryCount).filter(InventoryCount.id == count_id).first()
    if not count:
        return

    items = db.query(InventoryCountItem).filter(InventoryCountItem.count_id == count_id).all()
    count.total_items = len(items)
    count.matched_count = len([i for i in items if i.status == "matched" or (i.status == "pending" and i.diff_qty == 0)])
    count.discrepancy_count = len([i for i in items if i.status in ("discrepancy", "adjusted") or (i.status == "pending" and i.diff_qty != 0)])
    count.total_discrepancy_value = sum(abs(i.diff_value) for i in items)
