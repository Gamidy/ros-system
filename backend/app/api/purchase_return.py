"""采购退货管理 API: 退货单CRUD + 状态流转 + 统计 + 联动库存"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.purchase_return import PurchaseReturn, PurchaseReturnItem
from app.models.purchase import PurchaseOrder, GoodsReceipt, IncomingInspection
from app.models.inventory import Inventory, InventoryTransaction
from app.schemas.purchase_return import (
    ReturnCreate, ReturnUpdate, ReturnOut, ReturnItemOut, ReturnStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchases/returns", tags=["采购退货管理"])

RETURN_REASON_LABELS = {
    "quality": "品质不合格",
    "overdue": "逾期到货",
    "damaged": "运输损坏",
    "other": "其他原因",
}


def _generate_return_no(db: Session) -> str:
    """生成退货单号 PR-YYYYMMDD-XXXX"""
    from datetime import date
    today = date.today()
    prefix = f"PR-{today.strftime('%Y%m%d')}-"
    last = db.query(PurchaseReturn.return_no).filter(
        PurchaseReturn.return_no.like(f"{prefix}%")
    ).order_by(PurchaseReturn.id.desc()).first()
    if last:
        seq = int(last[0].split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


# ══════════════════════════════════════════════════
# 退货单 CRUD
# ══════════════════════════════════════════════════


@router.get("", response_model=dict)
def list_returns(
    status: Optional[str] = Query(None, description="筛选状态"),
    supplier_name: Optional[str] = Query(None),
    return_reason: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="搜索退货单号/物料"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """获取退货单列表（分页）"""
    q = db.query(PurchaseReturn)
    if status:
        q = q.filter(PurchaseReturn.status == status)
    if supplier_name:
        q = q.filter(PurchaseReturn.supplier_name.like(f"%{supplier_name}%"))
    if return_reason:
        q = q.filter(PurchaseReturn.return_reason == return_reason)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            PurchaseReturn.return_no.like(like)
            | PurchaseReturn.supplier_name.like(like)
            | PurchaseReturn.return_no.like(like)
        )

    total = q.count()
    returns = q.order_by(PurchaseReturn.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []
    for r in returns:
        items = db.query(PurchaseReturnItem).filter(
            PurchaseReturnItem.return_id == r.id
        ).all()
        result.append({
            "id": r.id,
            "return_no": r.return_no,
            "source_type": r.source_type,
            "source_id": r.source_id,
            "source_no": r.source_no,
            "supplier_name": r.supplier_name,
            "supplier_code": r.supplier_code,
            "order_id": r.order_id,
            "order_no": r.order_no,
            "return_date": r.return_date.isoformat() if r.return_date else None,
            "total_qty": r.total_qty,
            "total_amount": r.total_amount,
            "return_reason": r.return_reason,
            "return_reason_label": RETURN_REASON_LABELS.get(r.return_reason, r.return_reason),
            "reason_detail": r.reason_detail,
            "responsibility": r.responsibility,
            "logistics_company": r.logistics_company,
            "logistics_no": r.logistics_no,
            "refund_amount": r.refund_amount,
            "refund_date": r.refund_date.isoformat() if r.refund_date else None,
            "refund_method": r.refund_method,
            "status": r.status,
            "created_by": r.created_by,
            "approved_by": r.approved_by,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "items": [{
                "id": i.id, "part_no": i.part_no, "part_name": i.part_name,
                "spec": i.spec, "unit": i.unit, "return_qty": i.return_qty,
                "unit_price": i.unit_price, "total_price": i.total_price,
                "defect_type": i.defect_type, "defect_desc": i.defect_desc,
                "disposal": i.disposal, "remark": i.remark,
            } for i in items],
        })

    return {"total": total, "items": result, "page": page, "page_size": page_size}


@router.get("/stats", response_model=ReturnStatsOut)
def return_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """退货统计概览"""
    total = db.query(PurchaseReturn).count()
    draft = db.query(PurchaseReturn).filter(PurchaseReturn.status == "draft").count()
    pending = db.query(PurchaseReturn).filter(PurchaseReturn.status == "pending_approval").count()
    approved = db.query(PurchaseReturn).filter(PurchaseReturn.status == "approved").count()
    returned = db.query(PurchaseReturn).filter(PurchaseReturn.status == "returned").count()
    refunded = db.query(PurchaseReturn).filter(PurchaseReturn.status == "refunded").count()
    cancelled = db.query(PurchaseReturn).filter(PurchaseReturn.status == "cancelled").count()

    total_qty = db.query(func.coalesce(func.sum(PurchaseReturn.total_qty), 0)).scalar()
    total_amount = db.query(func.coalesce(func.sum(PurchaseReturn.total_amount), 0)).scalar()
    pending_refund = db.query(func.coalesce(func.sum(PurchaseReturn.total_amount), 0)).filter(
        PurchaseReturn.status.in_(["approved", "returned"])
    ).scalar() or 0

    return ReturnStatsOut(
        total_count=total,
        draft_count=draft,
        pending_count=pending,
        approved_count=approved,
        returned_count=returned,
        refunded_count=refunded,
        cancelled_count=cancelled,
        total_return_qty=float(total_qty or 0),
        total_return_amount=float(total_amount or 0),
        pending_refund_amount=float(pending_refund),
    )


@router.get("/{rid}", response_model=dict)
def get_return(
    rid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """获取退货单详情"""
    r = db.query(PurchaseReturn).filter(PurchaseReturn.id == rid).first()
    if not r:
        raise HTTPException(404, "退货单不存在")

    items = db.query(PurchaseReturnItem).filter(
        PurchaseReturnItem.return_id == r.id
    ).all()

    return {
        "id": r.id,
        "return_no": r.return_no,
        "source_type": r.source_type,
        "source_id": r.source_id,
        "source_no": r.source_no,
        "supplier_name": r.supplier_name,
        "supplier_code": r.supplier_code,
        "order_id": r.order_id,
        "order_no": r.order_no,
        "return_date": r.return_date.isoformat() if r.return_date else None,
        "total_qty": r.total_qty,
        "total_amount": r.total_amount,
        "return_reason": r.return_reason,
        "return_reason_label": RETURN_REASON_LABELS.get(r.return_reason, r.return_reason),
        "reason_detail": r.reason_detail,
        "responsibility": r.responsibility,
        "logistics_company": r.logistics_company,
        "logistics_no": r.logistics_no,
        "refund_amount": r.refund_amount,
        "refund_date": r.refund_date.isoformat() if r.refund_date else None,
        "refund_method": r.refund_method,
        "status": r.status,
        "created_by": r.created_by,
        "approved_by": r.approved_by,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "remark": r.remark,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "items": [{
            "id": i.id, "part_no": i.part_no, "part_name": i.part_name,
            "spec": i.spec, "unit": i.unit, "return_qty": i.return_qty,
            "unit_price": i.unit_price, "total_price": i.total_price,
            "inspection_item_id": i.inspection_item_id,
            "defect_type": i.defect_type, "defect_desc": i.defect_desc,
            "disposal": i.disposal, "remark": i.remark,
        } for i in items],
    }


@router.post("", response_model=dict, status_code=201)
def create_return(
    data: ReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """创建退货单"""
    if not data.items:
        raise HTTPException(400, "退货明细不能为空")

    return_no = _generate_return_no(db)
    total_qty = sum(i.return_qty for i in data.items)
    total_amount = sum(i.return_qty * i.unit_price for i in data.items)

    r = PurchaseReturn(
        return_no=return_no,
        source_type=data.source_type,
        source_id=data.source_id,
        source_no=data.source_no,
        supplier_name=data.supplier_name,
        supplier_code=data.supplier_code,
        order_id=data.order_id,
        order_no=data.order_no,
        total_qty=total_qty,
        total_amount=total_amount,
        return_reason=data.return_reason,
        reason_detail=data.reason_detail,
        responsibility=data.responsibility,
        logistics_company=data.logistics_company,
        logistics_no=data.logistics_no,
        created_by=data.created_by or current_user.username,
        remark=data.remark,
    )
    db.add(r)
    db.flush()

    for item_data in data.items:
        item = PurchaseReturnItem(
            return_id=r.id,
            part_no=item_data.part_no,
            part_name=item_data.part_name or item_data.part_no,
            spec=item_data.spec,
            unit=item_data.unit,
            return_qty=item_data.return_qty,
            unit_price=item_data.unit_price,
            total_price=item_data.return_qty * item_data.unit_price,
            inspection_item_id=item_data.inspection_item_id,
            defect_type=item_data.defect_type,
            defect_desc=item_data.defect_desc,
            disposal=item_data.disposal,
            remark=item_data.remark,
        )
        db.add(item)

    db.flush()
    db.commit()
    db.refresh(r)

    logger.info(
        "退货单创建: %s supplier=%s qty=%.1f amount=%.2f by=%s",
        return_no, data.supplier_name, total_qty, total_amount, current_user.username,
    )

    return {"id": r.id, "return_no": return_no, "message": "退货单创建成功"}


@router.put("/{rid}", response_model=dict)
def update_return(
    rid: int,
    data: ReturnUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """更新退货单（仅draft/pending_approval状态可修改）"""
    r = db.query(PurchaseReturn).filter(PurchaseReturn.id == rid).first()
    if not r:
        raise HTTPException(404, "退货单不存在")
    if r.status not in ("draft", "pending_approval"):
        raise HTTPException(400, f"当前状态为 {r.status}，不可修改")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)

    db.flush()
    db.commit()
    return {"message": "退货单已更新"}


@router.patch("/{rid}/status")
def update_return_status(
    rid: int,
    status: str = Query(..., pattern="^(pending_approval|cancelled|approved|returned|refunded)$"),
    refund_amount: Optional[float] = Query(None),
    refund_date: Optional[str] = Query(None),
    refund_method: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """更新退货单状态

    flow: draft → pending_approval → approved → returned → refunded
           ↓           ↓
        cancelled   cancelled
    """
    r = db.query(PurchaseReturn).filter(PurchaseReturn.id == rid).first()
    if not r:
        raise HTTPException(404, "退货单不存在")

    valid_transitions = {
        "draft": ["pending_approval", "cancelled"],
        "pending_approval": ["approved", "cancelled"],
        "approved": ["returned", "cancelled"],
        "returned": ["refunded"],
        "refunded": [],
        "cancelled": [],
    }

    if status not in valid_transitions.get(r.status, []):
        raise HTTPException(400, f"不允许从 {r.status} 变更为 {status}")

    old_status = r.status
    r.status = status

    if status == "approved":
        r.approved_by = current_user.username
        r.approved_at = datetime.utcnow()

    if status == "returned":
        if refund_amount is not None:
            r.refund_amount = refund_amount
        if refund_date:
            try:
                r.refund_date = datetime.fromisoformat(refund_date)
            except ValueError:
                pass
        if refund_method:
            r.refund_method = refund_method
        # 退货出库: 从库存扣减
        _deduct_inventory_on_return(db, r)

    if status == "refunded":
        if refund_amount is not None:
            r.refund_amount = refund_amount
        if refund_date:
            try:
                r.refund_date = datetime.fromisoformat(refund_date)
            except ValueError:
                pass
        if refund_method:
            r.refund_method = refund_method

    db.commit()
    logger.info(
        "退货单状态变更: %s %s→%s by=%s",
        r.return_no, old_status, status, current_user.username,
    )

    return {"message": f"退货单已变更为 {status}", "status": status}


@router.delete("/{rid}")
def delete_return(
    rid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """删除退货单（仅draft状态可删除）"""
    r = db.query(PurchaseReturn).filter(PurchaseReturn.id == rid).first()
    if not r:
        raise HTTPException(404, "退货单不存在")
    if r.status != "draft":
        raise HTTPException(400, f"当前状态 {r.status}，仅草稿可删除")
    db.delete(r)
    db.commit()
    return {"message": "退货单已删除"}


# ══════════════════════════════════════════════════
# 辅助: 退货出库扣减库存
# ══════════════════════════════════════════════════


def _deduct_inventory_on_return(db: Session, ret: PurchaseReturn):
    """退货出库: 减少库存 + 记录流水"""
    items = db.query(PurchaseReturnItem).filter(
        PurchaseReturnItem.return_id == ret.id
    ).all()

    for item in items:
        # 查找库存记录
        inv = db.query(Inventory).filter(
            Inventory.part_no == item.part_no,
        ).first()
        if not inv:
            logger.warning("退货扣库存找不到物料: %s", item.part_no)
            continue

        balance_before = inv.qty
        actual_return = min(item.return_qty, inv.qty)
        if actual_return <= 0:
            continue

        inv.qty -= actual_return
        inv.available_qty = max(0, inv.qty - inv.locked_qty)
        inv.total_value = inv.qty * inv.unit_cost

        # 记录流水
        txn = InventoryTransaction(
            warehouse_id=inv.warehouse_id,
            part_no=item.part_no,
            part_name=item.part_name,
            spec=item.spec,
            unit=item.unit,
            trans_type="out",
            qty=-actual_return,
            balance_before=balance_before,
            balance_after=inv.qty,
            ref_doc_type="purchase_return",
            ref_doc_id=ret.id,
            ref_doc_no=ret.return_no,
            operator=ret.created_by,
            remark=f"采购退货出库[{ret.return_no}]: {item.defect_desc or '质检不合格'}",
        )
        db.add(txn)
