"""外协管理模块 API — 外协厂商+外协订单+外协质检"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import date, datetime

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.outsource import (
    OutsourcePartner, OutsourceOrder, OutsourceOrderItem,
    OutsourceQualityRecord, OutsourceQualityFile,
)
from app.schemas.outsource import (
    OutsourcePartnerCreate, OutsourcePartnerUpdate, OutsourcePartnerOut, OutsourcePartnerListOut,
    OutsourceOrderCreate, OutsourceOrderUpdate, OutsourceOrderOut, OutsourceOrderListOut,
    OutsourceOrderItemOut,
    OutsourceQualityRecordCreate, OutsourceQualityRecordUpdate, OutsourceQualityRecordOut,
    OutsourceQualityRecordListOut,
)

router = APIRouter(prefix="/api/outsource", tags=["外协管理"])


def _auto_order_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(OutsourceOrder).filter(
        OutsourceOrder.order_no.like(f"OS-{today}-%")).count()
    return f"OS-{today}-{count + 1:04d}"


def _auto_partner_code(db: Session, ptype: str) -> str:
    prefix = {"mold": "M", "electrical": "E", "system": "S", "structural": "T", "other": "O"}
    p = prefix.get(ptype, "X")
    count = db.query(OutsourcePartner).filter(
        OutsourcePartner.code.like(f"OS-{p}-%")).count()
    return f"OS-{p}-{count + 1:04d}"


# ═══════════════ 外协厂商 CRUD ═══════════════

@router.get("/partners", response_model=OutsourcePartnerListOut)
def list_partners(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    partner_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutsourcePartnerListOut:
    query = db.query(OutsourcePartner)
    if partner_type:
        query = query.filter(OutsourcePartner.partner_type == partner_type)
    if status:
        query = query.filter(OutsourcePartner.status == status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(or_(OutsourcePartner.code.ilike(kw), OutsourcePartner.name.ilike(kw)))
    total = query.count()
    items = query.order_by(OutsourcePartner.id.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    result = []
    for p in items:
        out = OutsourcePartnerOut.model_validate(p)
        out.orders_count = len(p.orders) if p.orders else 0
        result.append(out)
    return {"items": result, "total": total}


@router.get("/partners/{pid}", response_model=OutsourcePartnerOut)
def get_partner(pid: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)) -> OutsourcePartnerOut:
    partner = db.query(OutsourcePartner).filter(OutsourcePartner.id == pid).first()
    if not partner:
        raise HTTPException(status_code=404, detail="外协厂商不存在")
    out = OutsourcePartnerOut.model_validate(partner)
    out.orders_count = len(partner.orders) if partner.orders else 0
    return out


@router.post("/partners", response_model=OutsourcePartnerOut,
             dependencies=[Depends(require_role("admin", "procurement", "rd_director"))])
def create_partner(data: OutsourcePartnerCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)) -> OutsourcePartnerOut:
    # 检查编码唯一
    existing = db.query(OutsourcePartner).filter(OutsourcePartner.code == data.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"厂商编码已存在: {data.code}")
    partner = OutsourcePartner(**data.model_dump())
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return OutsourcePartnerOut.model_validate(partner)


@router.put("/partners/{pid}", response_model=OutsourcePartnerOut,
            dependencies=[Depends(require_role("admin", "procurement", "rd_director"))])
def update_partner(pid: int, data: OutsourcePartnerUpdate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)) -> OutsourcePartnerOut:
    partner = db.query(OutsourcePartner).filter(OutsourcePartner.id == pid).first()
    if not partner:
        raise HTTPException(status_code=404, detail="外协厂商不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(partner, k, v)
    db.commit()
    db.refresh(partner)
    return OutsourcePartnerOut.model_validate(partner)


@router.delete("/partners/{pid}", dependencies=[Depends(require_role("admin"))])
def delete_partner(pid: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)) -> dict:
    partner = db.query(OutsourcePartner).filter(OutsourcePartner.id == pid).first()
    if not partner:
        raise HTTPException(status_code=404, detail="外协厂商不存在")
    db.delete(partner)
    db.commit()
    return {"ok": True}


# ═══════════════ 外协订单 CRUD ═══════════════

@router.get("/orders", response_model=OutsourceOrderListOut)
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    partner_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    order_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutsourceOrderListOut:
    query = db.query(OutsourceOrder).options(
        joinedload(OutsourceOrder.partner),
        joinedload(OutsourceOrder.items),
    )
    if partner_id:
        query = query.filter(OutsourceOrder.partner_id == partner_id)
    if project_id:
        query = query.filter(OutsourceOrder.project_id == project_id)
    if status:
        query = query.filter(OutsourceOrder.status == status)
    if order_type:
        query = query.filter(OutsourceOrder.order_type == order_type)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(or_(OutsourceOrder.order_no.ilike(kw), OutsourceOrder.title.ilike(kw)))
    total = query.count()
    items = query.order_by(OutsourceOrder.id.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    result = []
    for o in items:
        out = OutsourceOrderOut.model_validate(o)
        out.partner_name = o.partner.name if o.partner else ""
        out.items = [OutsourceOrderItemOut.model_validate(i) for i in (o.items or [])]
        result.append(out)
    return {"items": result, "total": total}


@router.get("/orders/{oid}", response_model=OutsourceOrderOut)
def get_order(oid: int, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)) -> OutsourceOrderOut:
    order = db.query(OutsourceOrder).options(
        joinedload(OutsourceOrder.partner),
        joinedload(OutsourceOrder.items),
        joinedload(OutsourceOrder.quality_records),
    ).filter(OutsourceOrder.id == oid).first()
    if not order:
        raise HTTPException(status_code=404, detail="外协订单不存在")
    out = OutsourceOrderOut.model_validate(order)
    out.partner_name = order.partner.name if order.partner else ""
    out.items = [OutsourceOrderItemOut.model_validate(i) for i in (order.items or [])]
    out.quality_records_count = len(order.quality_records) if order.quality_records else 0
    return out


@router.post("/orders", response_model=OutsourceOrderOut,
             dependencies=[Depends(require_role("admin", "procurement", "rd_director",
                                                  "structural_engineer", "systems_engineer"))])
def create_order(data: OutsourceOrderCreate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)) -> OutsourceOrderOut:
    partner = db.query(OutsourcePartner).filter(OutsourcePartner.id == data.partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="外协厂商不存在")
    items_data = data.items
    order_data = data.model_dump(exclude={"items"})
    order_data["order_no"] = _auto_order_no(db)
    order = OutsourceOrder(**order_data)
    db.add(order)
    db.flush()
    for item_data in items_data:
        db.add(OutsourceOrderItem(order_id=order.id, **item_data.model_dump()))
    db.commit()
    db.refresh(order)
    out = OutsourceOrderOut.model_validate(order)
    out.partner_name = partner.name
    return out


@router.put("/orders/{oid}", response_model=OutsourceOrderOut,
            dependencies=[Depends(require_role("admin", "procurement", "rd_director"))])
def update_order(oid: int, data: OutsourceOrderUpdate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)) -> OutsourceOrderOut:
    order = db.query(OutsourceOrder).options(
        joinedload(OutsourceOrder.partner),
        joinedload(OutsourceOrder.items),
    ).filter(OutsourceOrder.id == oid).first()
    if not order:
        raise HTTPException(status_code=404, detail="外协订单不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    db.commit()
    db.refresh(order)
    out = OutsourceOrderOut.model_validate(order)
    out.partner_name = order.partner.name if order.partner else ""
    out.items = [OutsourceOrderItemOut.model_validate(i) for i in (order.items or [])]
    return out


@router.delete("/orders/{oid}", dependencies=[Depends(require_role("admin"))])
def delete_order(oid: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)) -> dict:
    order = db.query(OutsourceOrder).filter(OutsourceOrder.id == oid).first()
    if not order:
        raise HTTPException(status_code=404, detail="外协订单不存在")
    db.delete(order)
    db.commit()
    return {"ok": True}


# ═══════════════ 外协质检 CRUD ═══════════════

@router.get("/quality-records", response_model=OutsourceQualityRecordListOut)
def list_quality_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_id: Optional[int] = Query(None),
    inspect_type: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutsourceQualityRecordListOut:
    query = db.query(OutsourceQualityRecord).options(
        joinedload(OutsourceQualityRecord.order))
    if order_id:
        query = query.filter(OutsourceQualityRecord.order_id == order_id)
    if inspect_type:
        query = query.filter(OutsourceQualityRecord.inspect_type == inspect_type)
    if result:
        query = query.filter(OutsourceQualityRecord.result == result)
    total = query.count()
    items = query.order_by(OutsourceQualityRecord.id.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    result_list = []
    for r in items:
        out = OutsourceQualityRecordOut.model_validate(r)
        out.order_title = r.order.title if r.order else ""
        result_list.append(out)
    return {"items": result_list, "total": total}


@router.post("/quality-records", response_model=OutsourceQualityRecordOut,
             dependencies=[Depends(require_role("admin", "quality_engineer", "procurement"))])
def create_quality_record(data: OutsourceQualityRecordCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)) -> OutsourceQualityRecordOut:
    order = db.query(OutsourceOrder).filter(OutsourceOrder.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="外协订单不存在")
    record = OutsourceQualityRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    out = OutsourceQualityRecordOut.model_validate(record)
    out.order_title = order.title
    return out


@router.put("/quality-records/{qid}", response_model=OutsourceQualityRecordOut,
            dependencies=[Depends(require_role("admin", "quality_engineer"))])
def update_quality_record(qid: int, data: OutsourceQualityRecordUpdate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)) -> OutsourceQualityRecordOut:
    record = db.query(OutsourceQualityRecord).options(
        joinedload(OutsourceQualityRecord.order)
    ).filter(OutsourceQualityRecord.id == qid).first()
    if not record:
        raise HTTPException(status_code=404, detail="质检记录不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    db.commit()
    db.refresh(record)
    out = OutsourceQualityRecordOut.model_validate(record)
    out.order_title = record.order.title if record.order else ""
    return out


@router.delete("/quality-records/{qid}", dependencies=[Depends(require_role("admin"))])
def delete_quality_record(qid: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)) -> dict:
    record = db.query(OutsourceQualityRecord).filter(OutsourceQualityRecord.id == qid).first()
    if not record:
        raise HTTPException(status_code=404, detail="质检记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
