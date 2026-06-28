"""采购订单 API: 订单管理 + 供应商管理 + 仪表盘"""
from datetime import date, datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.user import User
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier, OutsourceRequest, SupplierEvaluation, VALID_DIMENSIONS, DIMENSION_LABELS, GoodsReceipt, GoodsReceiptItem, IncomingInspection, InspectionStatus
from app.services import event_bus
from app.schemas import (
    SupplierCreate, SupplierOut, SupplierUpdate,
    EvaluationCreate, EvaluationOut, SupplierStatsOut,
    PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderDetailOut,
    PurchaseOrderStatusUpdate,
    PurchaseOrderItemCreate, PurchaseOrderItemOut, PurchaseOrderItemUpdate,
    PurchaseDashboardOut,
    OutsourceRequestCreate, OutsourceRequestOut, OutsourceRequestUpdate,
    ReceiptCreate, ReceiptOut, ReceiptItemOut, InspectionCreate, InspectionOut,
    QualityStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchases", tags=["采购订单管理"])


# ══════════════════════════════════════════════════
# Suppliers
# ══════════════════════════════════════════════════

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    keyword: str = "",
    status: str = "",
    category: str = "",
    sort_by: str = "overall_score",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    _=Depends(require_menu("purchases")),
) -> list[SupplierOut]:
    """列出所有供应商，支持关键词/状态/品类筛选和排序"""
    q = db.query(Supplier).filter(Supplier.is_deleted == 0)
    if keyword:
        q = q.filter(
            Supplier.name.like(f"%{keyword}%") |
            Supplier.code.like(f"%{keyword}%") |
            Supplier.contact.like(f"%{keyword}%")
        )
    if status:
        q = q.filter(Supplier.status == status)
    if category:
        q = q.filter(Supplier.category == category)
    # 排序
    sort_col = getattr(Supplier, sort_by, Supplier.overall_score)
    if sort_order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())
    return q.all()


@router.post("/suppliers", response_model=SupplierOut)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> SupplierOut:
    """创建供应商 — code全局唯一"""
    if db.query(Supplier).filter(Supplier.code == data.code).first():
        raise HTTPException(status_code=400, detail="供应商编码已存在")
    s = Supplier(**data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s


# ══════════════════════════════════════════════════
# Purchase Orders
# ══════════════════════════════════════════════════

@router.get("/orders", response_model=list[PurchaseOrderOut])
def list_orders(
    status: str = "",
    supplier: str = "",
    requester: str = "",
    date_from: str = "",
    date_to: str = "",
    db: Session = Depends(get_db),
    _=Depends(require_menu("purchases")),
) -> list[PurchaseOrderOut]:
    """列出采购订单，支持按status/supplier/requester/日期范围筛选"""
    q = db.query(PurchaseOrder)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if supplier:
        q = q.filter(
            PurchaseOrder.supplier_name.like(f"%{supplier}%") |
            PurchaseOrder.supplier_code.like(f"%{supplier}%")
        )
    if requester:
        q = q.filter(PurchaseOrder.requester.like(f"%{requester}%"))
    if date_from:
        q = q.filter(PurchaseOrder.created_at >= date_from)
    if date_to:
        q = q.filter(PurchaseOrder.created_at <= f"{date_to} 23:59:59")
    return q.order_by(PurchaseOrder.created_at.desc()).all()


@router.post("/orders", response_model=PurchaseOrderOut)
def create_order(data: PurchaseOrderCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> PurchaseOrderOut:
    """创建采购订单 — 自动生成单号"""
    # 自动生成 order_no: PO-YYYYMMDD-XXXX
    today_str = date.today().strftime("%Y%m%d")
    prefix = f"PO-{today_str}-"
    last = db.query(PurchaseOrder).filter(
        PurchaseOrder.order_no.like(f"{prefix}%")
    ).order_by(PurchaseOrder.id.desc()).first()

    if last and last.order_no.startswith(prefix):
        try:
            seq = int(last.order_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    order_no = f"{prefix}{seq:04d}"

    order = PurchaseOrder(
        order_no=order_no,
        **data.model_dump(exclude={"items"}),
    )
    db.add(order)
    db.flush()

    # 添加订单项
    items_data = data.items or []
    if items_data and all(item.unit_price <= 0 for item in items_data):
        raise HTTPException(status_code=400, detail="订单明细中至少需要一项单价>0")

    try:
        for item_data in items_data:
            item = PurchaseOrderItem(
                order_id=order.id,
                **item_data.model_dump(),
            )
            db.add(item)

        # 计算 total_amount
        db.flush()
        total = db.query(func.coalesce(func.sum(PurchaseOrderItem.total_price), 0)).filter(
            PurchaseOrderItem.order_id == order.id
        ).scalar()
        order.total_amount = float(total)

        db.commit()

        # ── event bus: purchase.order.created ──
        event_bus.emit(
            event_type="purchase.order.created",
            payload={
                "id": order.id,
                "order_no": order_no,
                "total_amount": float(total),
                "supplier_name": data.supplier_name,
            },
            source="purchases",
            producer="purchases.service",
            user_id=None,
        )

        db.refresh(order)
    except Exception as e:
        db.rollback()
        logger.error(f"采购订单创建失败: {e}")
        raise
    return order


@router.get("/orders/{order_id}", response_model=PurchaseOrderDetailOut)
def get_order(order_id: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))) -> PurchaseOrderDetailOut:
    """查看订单详情（含items）"""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="采购订单不存在")
    return order


@router.patch("/orders/{order_id}", response_model=PurchaseOrderOut)
def update_order_status(order_id: int, data: PurchaseOrderStatusUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> PurchaseOrderOut:
    """更新订单状态"""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="采购订单不存在")

    # 状态流转检查
    valid_transitions = {
        "draft": ["pending_approval", "cancelled"],
        "pending_approval": ["approved", "cancelled", "draft"],
        "approved": ["ordered", "cancelled"],
        "ordered": ["received", "cancelled"],
        "received": [],
        "cancelled": [],
    }
    allowed = valid_transitions.get(order.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"状态 {order.status} 不允许变更到 {data.status}，允许目标: {', '.join(allowed) if allowed else '无'}",
        )

    old_status = order.status
    order.status = data.status
    db.commit()
    db.refresh(order)

    # ── event bus: purchase.order.status_changed ──
    event_bus.emit(
        event_type="purchase.order.status_changed",
        payload={
            "id": order.id,
            "order_no": order.order_no,
            "from_status": old_status,
            "to_status": data.status,
        },
        source="purchases",
        producer="purchases.service",
        user_id=None,
    )

    # ── event bus: purchase.order.approved ──
    if data.status == "approved":
        event_bus.emit(
            event_type="purchase.order.approved",
            payload={
                "id": order.id,
                "order_no": order.order_no,
            },
            source="purchases",
            producer="purchases.service",
            user_id=None,
        )

    return order


# ══════════════════════════════════════════════════
# Orders Stats
# ══════════════════════════════════════════════════

@router.get("/orders/stats")
def get_order_stats(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))) -> dict:
    """返回订单统计数据"""
    total = db.query(PurchaseOrder).count()
    pending_approval = db.query(PurchaseOrder).filter(PurchaseOrder.status == "pending_approval").count()
    approved = db.query(PurchaseOrder).filter(PurchaseOrder.status == "approved").count()
    in_progress = db.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["ordered"])).count()
    completed = db.query(PurchaseOrder).filter(PurchaseOrder.status == "received").count()
    cancelled = db.query(PurchaseOrder).filter(PurchaseOrder.status == "cancelled").count()
    return {
        "total": total,
        "pending_approval": pending_approval,
        "approved": approved,
        "in_progress": in_progress,
        "completed": completed,
        "cancelled": cancelled,
    }


# ══════════════════════════════════════════════════
# Purchase Order Items
# ══════════════════════════════════════════════════

@router.post("/orders/{order_id}/items", response_model=PurchaseOrderItemOut)
def add_order_item(order_id: int, data: PurchaseOrderItemCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> PurchaseOrderItemOut:
    """添加订单项"""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="采购订单不存在")
    if order.status not in ("draft", "pending_approval"):
        raise HTTPException(status_code=400, detail="仅草稿或待审批状态可添加订单项")

    item = PurchaseOrderItem(order_id=order_id, **data.model_dump())
    db.add(item)

    # 重新计算总额
    db.flush()
    total = db.query(func.coalesce(func.sum(PurchaseOrderItem.total_price), 0)).filter(
        PurchaseOrderItem.order_id == order.id
    ).scalar()
    order.total_amount = float(total)

    db.commit(); db.refresh(item)
    return item


@router.patch("/orders/{order_id}/items/{item_id}", response_model=PurchaseOrderItemOut)
def update_order_item(order_id: int, item_id: int, data: PurchaseOrderItemUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> PurchaseOrderItemOut:
    """更新订单项"""
    item = db.query(PurchaseOrderItem).filter(
        PurchaseOrderItem.id == item_id,
        PurchaseOrderItem.order_id == order_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="订单项不存在")

    update_dict = data.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(item, k, v)

    # 重新计算小计
    if "quantity" in update_dict or "unit_price" in update_dict:
        item.total_price = item.quantity * item.unit_price

    db.flush()

    # 重新计算订单总额
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    total = db.query(func.coalesce(func.sum(PurchaseOrderItem.total_price), 0)).filter(
        PurchaseOrderItem.order_id == order.id
    ).scalar()
    order.total_amount = float(total)

    db.commit(); db.refresh(item)
    return item


# ══════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════

@router.get("/dashboard", response_model=PurchaseDashboardOut)
def purchase_dashboard(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))) -> PurchaseDashboardOut:
    """采购仪表盘数据（待审批数、本月采购额等）"""
    # 待审批订单数
    pending_count = db.query(PurchaseOrder).filter(
        PurchaseOrder.status == "pending_approval"
    ).count()

    # 本月采购额（已下单的订单）
    first_of_month = date.today().replace(day=1)
    month_total = db.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).filter(
        PurchaseOrder.status.in_(["ordered", "received"]),
        PurchaseOrder.updated_at >= first_of_month,
    ).scalar()

    # 本月订单数
    month_order_count = db.query(PurchaseOrder).filter(
        PurchaseOrder.created_at >= first_of_month,
    ).count()

    # 待收货订单数
    received_pending = db.query(PurchaseOrder).filter(
        PurchaseOrder.status == "ordered"
    ).count()

    # 各状态订单数
    status_breakdown = {}
    for s in ["draft", "pending_approval", "approved", "ordered", "received", "cancelled"]:
        cnt = db.query(PurchaseOrder).filter(PurchaseOrder.status == s).count()
        if cnt > 0:
            status_breakdown[s] = cnt

    return PurchaseDashboardOut(
        pending_approval=pending_count,
        month_total_amount=float(month_total),
        month_order_count=month_order_count,
        pending_received=received_pending,
        total_orders=db.query(PurchaseOrder).count(),
        total_suppliers=db.query(Supplier).count(),
        status_breakdown=status_breakdown,
    )


# ══════════════════════════════════════════════════
# Outsource Requests (外协送样流程)
# ══════════════════════════════════════════════════

@router.get("/outsource-requests", response_model=list[OutsourceRequestOut])
def list_outsource_requests(
    status: str = "",
    product_code: str = "",
    db: Session = Depends(get_db),
    _=Depends(require_menu("purchases")),
) -> list[OutsourceRequestOut]:
    """列出外协送样申请"""
    q = db.query(OutsourceRequest)
    if status:
        q = q.filter(OutsourceRequest.status == status)
    if product_code:
        q = q.filter(OutsourceRequest.product_code == product_code)
    return q.order_by(OutsourceRequest.created_at.desc()).all()


@router.post("/outsource-requests", response_model=OutsourceRequestOut)
def create_outsource_request(
    data: OutsourceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "procurement")),
) -> OutsourceRequestOut:
    """创建外协送样申请 — 自动生成请求编号 OS-YYYYMMDD-XXXX"""
    today_str = date.today().strftime("%Y%m%d")
    prefix = f"OS-{today_str}-"
    last = db.query(OutsourceRequest).filter(
        OutsourceRequest.request_no.like(f"{prefix}%")
    ).order_by(OutsourceRequest.id.desc()).first()

    if last and last.request_no.startswith(prefix):
        try:
            seq = int(last.request_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    request_no = f"{prefix}{seq:04d}"

    req = OutsourceRequest(
        request_no=request_no,
        created_by=current_user.username,
        **data.model_dump(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/outsource-requests/{req_id}", response_model=OutsourceRequestOut)
def get_outsource_request(req_id: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))) -> OutsourceRequestOut:
    """查看外协送样申请详情"""
    req = db.query(OutsourceRequest).filter(OutsourceRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="外协送样申请不存在")
    return req


@router.patch("/outsource-requests/{req_id}", response_model=OutsourceRequestOut)
def update_outsource_request(
    req_id: int,
    data: OutsourceRequestUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "procurement")),
) -> OutsourceRequestOut:
    """更新外协送样申请（状态/交期/说明）"""
    req = db.query(OutsourceRequest).filter(OutsourceRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="外协送样申请不存在")

    update_dict = data.model_dump(exclude_unset=True)
    if "status" in update_dict:
        valid_statuses = ["pending", "approved", "rejected", "completed"]
        if update_dict["status"] not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"无效状态，允许: {', '.join(valid_statuses)}")

    for k, v in update_dict.items():
        setattr(req, k, v)

    db.commit()
    db.refresh(req)

    # ── event bus: outsource.partner.evaluated ──
    if "status" in update_dict and update_dict["status"] in ("approved", "completed"):
        event_bus.emit(
            event_type="outsource.partner.evaluated",
            payload={
                "id": req.id,
                "request_no": req.request_no,
                "status": req.status,
                "product_code": req.product_code,
            },
            source="purchases",
            producer="purchases.service",
            user_id=None,
        )

    return req


# ══════════════════════════════════════════════════
# 供应商详情/删除
# ══════════════════════════════════════════════════


@router.get("/suppliers/{sid}", response_model=SupplierOut)
def get_supplier(sid: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))) -> SupplierOut:
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    return s


@router.patch("/suppliers/{sid}", response_model=SupplierOut)
def update_supplier(sid: int, data: SupplierUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> SupplierOut:
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "code" in updates and updates["code"] != s.code:
        if db.query(Supplier).filter(Supplier.code == updates["code"], Supplier.id != sid, Supplier.is_deleted == 0).first():
            raise HTTPException(400, f"编码 '{updates['code']}' 已被使用")
    for k, v in updates.items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    return s


@router.delete("/suppliers/{sid}")
def delete_supplier(sid: int, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement"))) -> dict:
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    s.is_deleted = 1
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
# 供应商评估
# ══════════════════════════════════════════════════


@router.get("/suppliers/{sid}/evaluations", response_model=list[EvaluationOut])
def list_evaluations(sid: int, db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    evals = db.query(SupplierEvaluation).filter(SupplierEvaluation.supplier_id == sid).order_by(SupplierEvaluation.evaluated_at.desc()).all()
    return [EvaluationOut(id=e.id, supplier_id=e.supplier_id, dimension=e.dimension, dimension_label=DIMENSION_LABELS.get(e.dimension, e.dimension), score=e.score, weight=e.weight, comment=e.comment, evaluator=e.evaluator, evaluated_at=e.evaluated_at) for e in evals]


@router.post("/suppliers/{sid}/evaluations", response_model=EvaluationOut)
def create_evaluation(sid: int, data: EvaluationCreate, db: Session = Depends(get_db), _=Depends(require_role("admin", "general_manager", "procurement", "quality_engineer"))):
    s = db.query(Supplier).filter(Supplier.id == sid, Supplier.is_deleted == 0).first()
    if not s: raise HTTPException(404, "供应商不存在")
    if data.dimension not in VALID_DIMENSIONS:
        raise HTTPException(400, f"无效维度: {data.dimension}")
    ev = SupplierEvaluation(supplier_id=sid, dimension=data.dimension, score=data.score, weight=data.weight, comment=data.comment, evaluator=data.evaluator)
    db.add(ev)
    # 重算总分
    latest = {}
    for e in db.query(SupplierEvaluation).filter(SupplierEvaluation.supplier_id == sid).order_by(SupplierEvaluation.evaluated_at.desc()).all():
        if e.dimension not in latest: latest[e.dimension] = (e.score, e.weight)
    if latest:
        tw = sum(w for _, w in latest.values())
        s.overall_score = round(sum(s * w for s, w in latest.values()) / tw, 1) if tw > 0 else round(sum(s for s, _ in latest.values()) / len(latest), 1)
    db.commit(); db.refresh(ev)
    return EvaluationOut(id=ev.id, supplier_id=ev.supplier_id, dimension=ev.dimension, dimension_label=DIMENSION_LABELS.get(ev.dimension, ev.dimension), score=ev.score, weight=ev.weight, comment=ev.comment, evaluator=ev.evaluator, evaluated_at=ev.evaluated_at)


# ══════════════════════════════════════════════════
# 供应商聚合统计
# ══════════════════════════════════════════════════


@router.get("/suppliers/stats/summary", response_model=SupplierStatsOut)
def supplier_stats_summary(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    base = db.query(Supplier).filter(Supplier.is_deleted == 0)
    total = base.count()
    scores = [s.overall_score or 0 for s in base.all() if s.overall_score]
    cats = db.query(Supplier.category).filter(Supplier.is_deleted == 0, Supplier.category.isnot(None), Supplier.category != "").distinct().count()
    return SupplierStatsOut(total_count=total, qualified_count=base.filter(Supplier.status == "qualified").count(), active_count=base.filter(Supplier.status == "active").count(), suspended_count=base.filter(Supplier.status == "suspended").count(), blacklisted_count=base.filter(Supplier.status == "blacklisted").count(), avg_score=round(sum(scores)/len(scores), 1) if scores else 0, low_score_count=sum(1 for s in scores if s < 60), category_count=cats)


@router.get("/suppliers/ranking/list")
def supplier_ranking(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    suppliers = db.query(Supplier).filter(Supplier.is_deleted == 0).order_by(Supplier.overall_score.desc()).limit(limit).all()
    last_eval = dict(db.query(SupplierEvaluation.supplier_id, func.max(SupplierEvaluation.evaluated_at)).filter(SupplierEvaluation.supplier_id.in_([s.id for s in suppliers])).group_by(SupplierEvaluation.supplier_id).all())
    return [{"id": s.id, "name": s.name, "code": s.code, "category": s.category, "overall_score": s.overall_score or 0, "status": s.status, "evaluation_count": db.query(func.count(SupplierEvaluation.id)).filter(SupplierEvaluation.supplier_id == s.id).scalar() or 0, "last_evaluated": str(last_eval.get(s.id, "")) if last_eval.get(s.id) else None} for s in suppliers]


@router.get("/suppliers/categories/list")
def supplier_categories(db: Session = Depends(get_db), _=Depends(require_menu("purchases"))):
    rows = db.query(Supplier.category, func.count(Supplier.id).label("cnt")).filter(Supplier.is_deleted == 0, Supplier.category.isnot(None), Supplier.category != "").group_by(Supplier.category).order_by(func.count(Supplier.id).desc()).all()
    return [{"category": r.category, "count": r.cnt} for r in rows]


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
        try: seq = int(last.receipt_no.split("-")[-1]) + 1
        except: seq = 1
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
    from sqlalchemy import func, case

    # 整体统计
    total = db.query(IncomingInspection).count()
    pass_count = db.query(IncomingInspection).filter(IncomingInspection.result == "pass").count()
    concession_count = db.query(IncomingInspection).filter(IncomingInspection.result == "concession").count()
    reject_count = db.query(IncomingInspection).filter(IncomingInspection.result == "reject").count()

    def rate(n: int) -> float:
        return round(n / total * 100, 1) if total > 0 else 0.0

    # 本月统计
    from datetime import datetime
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

    # 月度趋势（近12个月）— 分批查询用月份字符串对比
    trend = []
    now_str = now.strftime("%Y-%m")
    for i in range(11, -1, -1):
        # 计算月份偏移
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
