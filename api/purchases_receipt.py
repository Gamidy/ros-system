"""采购订单 API — 收货管理模块"""
from datetime import date, datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.user import User
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem, IncomingInspection, InspectionStatus
from app.schemas import (
    ReceiptCreate, ReceiptOut, ReceiptItemOut, InspectionCreate, InspectionOut,
    QualityStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchases", tags=["采购订单管理-收货"])


# ══════════════════════════════════════════════════
# 采购收货管理
# ══════════════════════════════════════════════════


@router.get("/receipts", response_model=list[ReceiptOut])
def list_receipts(
    keyword: str = "", status: str = "",
    date_from: str = "", date_to: str = "",
    db: Session = Depends(get_db), _=Depends(require_menu("purchases")),
):
    q = db.query(GoodsReceipt)
    if keyword:
        q = q.filter(
            GoodsReceipt.receipt_no.like(f"%{keyword}%") |
            GoodsReceipt.supplier_name.like(f"%{keyword}%")
        )
    if status: q = q.filter(GoodsReceipt.status == status)
    if date_from: q = q.filter(GoodsReceipt.received_date >= date_from)
    if date_to: q = q.filter(GoodsReceipt.received_date <= f"{date_to} 23:59:59")
    return q.order_by(GoodsReceipt.created_at.desc()).all()


@router.get("/receipts/{rid}", response_model=ReceiptOut)
def get_receipt(rid: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    r = db.query(GoodsReceipt).filter(GoodsReceipt.id == rid).first()
    if not r: raise HTTPException(404, "收货单不存在")
    return r


@router.post("/receipts", response_model=ReceiptOut)
def create_receipt(data: ReceiptCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _=Depends(require_role("admin", "general_manager", "procurement"))):
    # 验证PO
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == data.order_id).first()
    if not po: raise HTTPException(400, "采购订单不存在")
    if po.status not in ("ordered", "approved"):
        raise HTTPException(400, f"订单状态 {po.status} 不允许收货，需为 ordered/approved")

    # 自动生成单号
    prefix = f"GR-{date.today().strftime('%Y%m%d')}-"
    last = db.query(GoodsReceipt).filter(GoodsReceipt.receipt_no.like(f"{prefix}%")).order_by(GoodsReceipt.id.desc()).first()
    seq = 1
    if last and last.receipt_no.startswith(prefix):
        try:
            seq = int(last.receipt_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    receipt_no = f"{prefix}{seq:04d}"

    total_qty = sum(it.received_qty for it in data.items)
    total_amount = sum(it.received_qty * it.unit_price for it in data.items)

    receipt = GoodsReceipt(
        receipt_no=receipt_no, order_id=data.order_id,
        supplier_name=po.supplier_name, supplier_code=po.supplier_code,
        warehouse=data.warehouse, location=data.location,
        total_qty=total_qty, total_amount=total_amount,
        remark=data.remark, created_by=current_user.username,
    )
    db.add(receipt); db.flush()

    for it in data.items:
        item = GoodsReceiptItem(
            receipt_id=receipt.id, order_item_id=it.order_item_id,
            part_no=it.part_no, part_name=it.part_name, spec=it.spec,
            unit=it.unit, ordered_qty=it.ordered_qty,
            received_qty=it.received_qty, unit_price=it.unit_price,
            total_price=it.received_qty * it.unit_price,
        )
        db.add(item)

        # 更新PO明细已收货数量
        if it.order_item_id:
            poi = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.id == it.order_item_id).first()
            if poi:
                poi.received_qty = (poi.received_qty or 0) + it.received_qty

    # 更新PO状态: 检查是否全部收货
    all_items = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.order_id == data.order_id).all()
    all_received = all(
        (i.received_qty or 0) >= i.quantity for i in all_items
    ) if all_items else False
    if all_received:
        po.status = "received"

    db.commit(); db.refresh(receipt)
    return receipt


@router.delete("/receipts/{rid}")
def delete_receipt(rid: int, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))):
    r = db.query(GoodsReceipt).filter(GoodsReceipt.id == rid).first()
    if not r: raise HTTPException(404, "收货单不存在")
    if r.status != "pending_inspection":
        raise HTTPException(400, f"状态 {r.status} 不允许删除")
    db.delete(r); db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
# 来料检验
# ══════════════════════════════════════════════════


@router.get("/receipts/{rid}/inspections", response_model=list[InspectionOut])
def list_inspections(rid: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    return db.query(IncomingInspection).filter(IncomingInspection.receipt_id == rid).order_by(IncomingInspection.inspected_at.desc()).all()


@router.post("/inspections", response_model=InspectionOut)
def create_inspection(data: InspectionCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement", "quality_engineer"))):
    receipt = db.query(GoodsReceipt).filter(GoodsReceipt.id == data.receipt_id).first()
    if not receipt: raise HTTPException(400, "收货单不存在")

    insp = IncomingInspection(**data.model_dump())
    db.add(insp)

    # 更新收货明细的accepted/rejected数量
    if data.receipt_item_id:
        item = db.query(GoodsReceiptItem).filter(GoodsReceiptItem.id == data.receipt_item_id).first()
        if item:
            item.accepted_qty = item.received_qty - data.defect_qty
            item.rejected_qty = data.defect_qty

    # 更新收货单状态
    if data.result == InspectionStatus.REJECT:
        receipt.status = "rejected"
    elif data.result == InspectionStatus.CONCESSION:
        receipt.status = "inspected"
    else:
        receipt.status = "inspected"

    db.commit(); db.refresh(insp)
    return insp


@router.get("/receipts/stats/summary")
def receipt_stats(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    total = db.query(GoodsReceipt).count()
    pending = db.query(GoodsReceipt).filter(GoodsReceipt.status == "pending_inspection").count()
    inspected = db.query(GoodsReceipt).filter(GoodsReceipt.status == "inspected").count()
    rejected = db.query(GoodsReceipt).filter(GoodsReceipt.status == "rejected").count()
    return {"total": total, "pending_inspection": pending, "inspected": inspected, "rejected": rejected}


# ══════════════════════════════════════════════════
# 采购质检统计看板
# ══════════════════════════════════════════════════


@router.get("/quality-stats", response_model=QualityStatsOut)
def quality_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("purchases")),
):
    """采购质检统计看板 — 合格率/供应商排名/趋势/缺陷分析"""

    # 整体统计
    total = db.query(IncomingInspection).count()
    pass_count = db.query(IncomingInspection).filter(IncomingInspection.result == "pass").count()
    concession_count = db.query(IncomingInspection).filter(IncomingInspection.result == "concession").count()
    reject_count = db.query(IncomingInspection).filter(IncomingInspection.result == "reject").count()

    def rate(n: int) -> float:
        return round(n / total * 100, 1) if total > 0 else 0.0

    # 本月统计
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_total = db.query(IncomingInspection).filter(IncomingInspection.inspected_at >= month_start).count()
    month_pass = db.query(IncomingInspection).filter(
        IncomingInspection.inspected_at >= month_start,
        IncomingInspection.result == "pass",
    ).count()

    # 按供应商统计 — 通过收货单关联到供应商
    supplier_stats = db.query(
        GoodsReceipt.supplier_name,
        GoodsReceipt.supplier_code,
        func.count(IncomingInspection.id).label("total"),
        func.sum(case((IncomingInspection.result == "pass", 1), else_=0)).label("pass_cnt"),
        func.sum(case((IncomingInspection.result == "concession", 1), else_=0)).label("concession_cnt"),
        func.sum(case((IncomingInspection.result == "reject", 1), else_=0)).label("reject_cnt"),
    ).join(
        GoodsReceipt, IncomingInspection.receipt_id == GoodsReceipt.id,
    ).group_by(
        GoodsReceipt.supplier_name, GoodsReceipt.supplier_code,
    ).order_by(
        func.count(IncomingInspection.id).desc(),
    ).all()

    by_supplier = []
    for s in supplier_stats:
        st = int(s.total) or 0
        pc = int(s.pass_cnt) or 0
        by_supplier.append({
            "supplier_name": s.supplier_name,
            "supplier_code": s.supplier_code,
            "total_inspections": st,
            "pass_count": pc,
            "concession_count": int(s.concession_cnt) or 0,
            "reject_count": int(s.reject_cnt) or 0,
            "pass_rate": round(pc / st * 100, 1) if st > 0 else 0.0,
        })

    # 月度趋势（近12个月）
    trend = []
    now_str = now.strftime("%Y-%m")
    for i in range(11, -1, -1):
        y = now.year
        m = now.month - i
        while m <= 0:
            y -= 1
            m += 12
        month_str = f"{y:04d}-{m:02d}"
        next_m = m + 1
        next_y = y
        if next_m > 12:
            next_m = 1
            next_y += 1
        month_start_str = f"{y:04d}-{m:02d}-01"
        month_end_str = f"{next_y:04d}-{next_m:02d}-01"

        mt = db.query(IncomingInspection).filter(
            IncomingInspection.inspected_at >= month_start_str,
            IncomingInspection.inspected_at < month_end_str,
        ).count()
        mp = db.query(IncomingInspection).filter(
            IncomingInspection.inspected_at >= month_start_str,
            IncomingInspection.inspected_at < month_end_str,
            IncomingInspection.result == "pass",
        ).count()
        mr = db.query(IncomingInspection).filter(
            IncomingInspection.inspected_at >= month_start_str,
            IncomingInspection.inspected_at < month_end_str,
            IncomingInspection.result == "reject",
        ).count()
        trend.append({
            "month": month_str,
            "total": mt,
            "pass_count": mp,
            "reject_count": mr,
            "pass_rate": round(mp / mt * 100, 1) if mt > 0 else 0.0,
        })

    # 缺陷分类 TOP10
    defects = db.query(
        IncomingInspection.defect_desc,
        func.count(IncomingInspection.id).label("cnt"),
    ).filter(
        IncomingInspection.defect_desc.isnot(None),
        IncomingInspection.defect_desc != "",
    ).group_by(
        IncomingInspection.defect_desc,
    ).order_by(
        func.count(IncomingInspection.id).desc(),
    ).limit(10).all()

    top_defects = [{"defect_desc": d.defect_desc, "count": int(d.cnt)} for d in defects]

    # 最近不合格记录
    recent_rejects_raw = db.query(IncomingInspection).filter(
        IncomingInspection.result.in_(["reject", "concession"]),
    ).order_by(
        IncomingInspection.inspected_at.desc(),
    ).limit(10).all()

    recent_rejects = []
    for r in recent_rejects_raw:
        receipt_info = db.query(GoodsReceipt).filter(GoodsReceipt.id == r.receipt_id).first()
        recent_rejects.append({
            "id": r.id,
            "part_no": r.part_no,
            "result": r.result,
            "defect_desc": r.defect_desc,
            "defect_qty": r.defect_qty,
            "sample_qty": r.sample_qty,
            "supplier_name": receipt_info.supplier_name if receipt_info else "",
            "inspector": r.inspector,
            "inspected_at": r.inspected_at.isoformat() if r.inspected_at else None,
        })

    return {
        "total_inspections": total,
        "pass_rate": rate(pass_count),
        "concession_rate": rate(concession_count),
        "reject_rate": rate(reject_count),
        "month_total": month_total,
        "month_pass_rate": round(month_pass / month_total * 100, 1) if month_total > 0 else 0.0,
        "by_supplier": by_supplier,
        "trend": trend,
        "top_defects": top_defects,
        "recent_rejects": recent_rejects,
    }
