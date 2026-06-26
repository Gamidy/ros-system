"""采购订单 API: 订单管理 + 供应商管理 + 仪表盘"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.user import User
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier, OutsourceRequest
from app.schemas import (
    SupplierCreate, SupplierOut, SupplierUpdate,
    PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderDetailOut,
    PurchaseOrderStatusUpdate,
    PurchaseOrderItemCreate, PurchaseOrderItemOut, PurchaseOrderItemUpdate,
    PurchaseDashboardOut,
    OutsourceRequestCreate, OutsourceRequestOut, OutsourceRequestUpdate,
)

router = APIRouter(prefix="/purchases", tags=["采购订单管理"])


# ══════════════════════════════════════════════════
# Suppliers
# ══════════════════════════════════════════════════

@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    keyword: str = "",
    status: str = "",
    db: Session = Depends(get_db),
    _=Depends(require_menu("purchases")),
) -> list[SupplierOut]:
    """列出所有供应商，支持关键词/状态筛选"""
    q = db.query(Supplier)
    if keyword:
        q = q.filter(
            Supplier.name.like(f"%{keyword}%") |
            Supplier.code.like(f"%{keyword}%")
        )
    if status:
        q = q.filter(Supplier.status == status)
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
        db.refresh(order)
    except Exception:
        db.rollback()
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

    order.status = data.status
    db.commit(); db.refresh(order)
    return order


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
    return req
