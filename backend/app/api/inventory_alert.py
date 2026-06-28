"""库存预警与补货建议 API"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu
from app.models.user import User
from app.models.inventory import Inventory, ReplenishmentSuggestion, Warehouse
from app.models.alert import Alert, Notification
from app.schemas.inventory import (
    ReplenishmentSuggestionCreate, ReplenishmentSuggestionUpdate,
    ReplenishmentSuggestionOut, ReplenishmentStatsOut,
    InventoryAlertCheckResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["库存预警与补货"])


# ══════════════════════════════════════════════════
# 库存预警检查
# ══════════════════════════════════════════════════


@router.post("/alert-check", response_model=InventoryAlertCheckResult)
def check_inventory_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """扫描全部库存，自动生成低库存/再订货预警

    逻辑:
      - 低库存预警: qty <= min_stock (且 min_stock > 0)
      - 再订货预警: qty <= reorder_point (且 reorder_point > 0) 且 qty > min_stock
      已有未解决的同物料预警则跳过，避免重复。
    """
    items = db.query(Inventory).filter(
        Inventory.min_stock > 0,
        Inventory.qty <= Inventory.min_stock,
    ).all()

    reorder_items = db.query(Inventory).filter(
        Inventory.reorder_point > 0,
        Inventory.qty <= Inventory.reorder_point,
        Inventory.qty > Inventory.min_stock,
    ).all()

    created_count = 0
    alert_items = []

    # 低库存预警
    for inv in items:
        existing = db.query(Alert).filter(
            Alert.target_type == "inventory",
            Alert.target_id == inv.id,
            Alert.alert_type == "low_stock",
            Alert.is_resolved == False,
        ).first()
        if existing:
            continue

        wh_name = inv.warehouse.name if inv.warehouse else "未知仓库"
        alert = Alert(
            target_type="inventory",
            target_id=inv.id,
            title=f"低库存预警: {inv.part_name or inv.part_no}",
            level=1 if inv.qty <= 0 else 2,
            alert_type="low_stock",
            message=(
                f"物料 [{inv.part_no}] {inv.part_name or ''} "
                f"在仓库 [{wh_name}] 当前库存 {inv.qty} {inv.unit}, "
                f"低于最低库存线 {inv.min_stock}{inv.unit}, "
                f"建议立即补货"
            ),
        )
        db.add(alert)
        created_count += 1
        alert_items.append({
            "part_no": inv.part_no,
            "part_name": inv.part_name,
            "warehouse_name": wh_name,
            "qty": inv.qty,
            "threshold": inv.min_stock,
            "level": "紧急" if inv.qty <= 0 else "警告",
        })

    # 再订货提醒
    for inv in reorder_items:
        existing = db.query(Alert).filter(
            Alert.target_type == "inventory",
            Alert.target_id == inv.id,
            Alert.alert_type == "reorder",
            Alert.is_resolved == False,
        ).first()
        if existing:
            continue

        wh_name = inv.warehouse.name if inv.warehouse else "未知仓库"
        alert = Alert(
            target_type="inventory",
            target_id=inv.id,
            title=f"建议补货: {inv.part_name or inv.part_no}",
            level=3,
            alert_type="reorder",
            message=(
                f"物料 [{inv.part_no}] {inv.part_name or ''} "
                f"在仓库 [{wh_name}] 当前库存 {inv.qty} {inv.unit}, "
                f"已达再订货点 {inv.reorder_point}{inv.unit}, 建议安排采购"
            ),
        )
        db.add(alert)
        created_count += 1
        # 不重复添加到 alert_items，已经在低库存预警中覆盖了更严重的情况

    if created_count > 0:
        db.commit()

    return InventoryAlertCheckResult(
        total_checked=db.query(Inventory).count(),
        low_stock_count=len(items),
        reorder_count=len(reorder_items),
        alerts_created=created_count,
        items=alert_items,
    )


@router.get("/alerts", response_model=dict)
def list_inventory_alerts(
    alert_type: Optional[str] = Query(None, description="low_stock/reorder"),
    is_resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """获取库存预警列表（从 Alert 表查询）"""
    q = db.query(Alert).filter(Alert.target_type == "inventory")
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    if is_resolved is not None:
        q = q.filter(Alert.is_resolved == is_resolved)

    alerts = q.order_by(Alert.created_at.desc()).limit(200).all()
    result = []
    for a in alerts:
        inv = db.query(Inventory).filter(Inventory.id == a.target_id).first()
        result.append({
            "id": a.id,
            "target_id": a.target_id,
            "part_no": inv.part_no if inv else None,
            "part_name": inv.part_name if inv else None,
            "warehouse_id": inv.warehouse_id if inv else None,
            "warehouse_name": inv.warehouse.name if inv and inv.warehouse else None,
            "current_qty": inv.qty if inv else None,
            "min_stock": inv.min_stock if inv else None,
            "reorder_point": inv.reorder_point if inv else None,
            "title": a.title,
            "level": a.level,
            "alert_type": a.alert_type,
            "message": a.message,
            "is_read": a.is_read,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return {"total": len(result), "items": result}


@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """标记预警为已处理"""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.target_type == "inventory",
    ).first()
    if not alert:
        raise HTTPException(404, "预警记录不存在")
    alert.is_resolved = True
    alert.resolved_by = current_user.username
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "预警已标记为已处理"}


# ══════════════════════════════════════════════════
# 补货建议管理
# ══════════════════════════════════════════════════


@router.post("/replenishments/generate", response_model=dict)
def generate_replenishment_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """自动生成补货建议

    基于库存中低于再订货点/最低库存线的物料，自动计算建议补货量。
    计算逻辑:
      - 建议补货量 = max(min_stock - qty, reorder_point * 2 - qty)
      - 若已有待审核的补货建议则跳过
    """
    candidates = db.query(Inventory).filter(
        Inventory.reorder_point > 0,
        Inventory.qty <= Inventory.reorder_point,
    ).all()

    # 加上低库存物料（即使没有设置 reorder_point）
    low_stock = db.query(Inventory).filter(
        Inventory.min_stock > 0,
        Inventory.qty <= Inventory.min_stock,
        Inventory.reorder_point == 0,
    ).all()

    all_items = list(set(candidates + low_stock))
    created = 0
    skipped = 0
    items = []

    for inv in all_items:
        # 跳过已有待审核建议的物料
        existing = db.query(ReplenishmentSuggestion).filter(
            ReplenishmentSuggestion.warehouse_id == inv.warehouse_id,
            ReplenishmentSuggestion.part_no == inv.part_no,
            ReplenishmentSuggestion.status == "pending",
        ).first()
        if existing:
            skipped += 1
            continue

        # 计算建议补货量
        target = max(inv.min_stock, inv.reorder_point * 2) if inv.reorder_point > 0 else inv.min_stock
        if target <= 0:
            target = inv.reorder_point or inv.min_stock or inv.qty * 2
        suggested = max(target - inv.qty, 1)

        # 计算日均消耗（近30天出库流水）
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        usage_data = db.query(
            func.coalesce(func.sum(func.abs(Inventory.qty)), 0)
        ).select_from(Inventory).filter(
            Inventory.warehouse_id == inv.warehouse_id,
            Inventory.part_no == inv.part_no,
            # 这里需要关联流水表才能做精确计算，简化版用总出库量
        ).first()
        avg_usage = round(float(usage_data[0]) / 30, 2) if usage_data and usage_data[0] else 0

        total_cost = suggested * inv.unit_cost

        suggestion = ReplenishmentSuggestion(
            warehouse_id=inv.warehouse_id,
            part_no=inv.part_no,
            part_name=inv.part_name,
            spec=inv.spec,
            unit=inv.unit,
            current_qty=inv.qty,
            reorder_point=inv.reorder_point,
            min_stock=inv.min_stock,
            avg_daily_usage=avg_usage,
            suggested_qty=suggested,
            lead_time_days=7,
            unit_cost=inv.unit_cost,
            total_cost=total_cost,
            status="pending",
            source="auto",
            operator=current_user.username,
            remark=f"自动生成: 当前库存{inv.qty}{inv.unit}, 建议补货{suggested}{inv.unit}",
        )
        db.add(suggestion)
        created += 1
        items.append({
            "part_no": inv.part_no,
            "part_name": inv.part_name,
            "current_qty": inv.qty,
            "suggested_qty": suggested,
            "total_cost": total_cost,
        })

    if created > 0:
        db.commit()

    return {
        "total_candidates": len(all_items),
        "created": created,
        "skipped": skipped,
        "items": items,
    }


@router.get("/replenishments", response_model=dict)
def list_replenishments(
    status: Optional[str] = Query(None, description="pending/approved/purchased/cancelled"),
    warehouse_id: Optional[int] = Query(None),
    part_no: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """获取补货建议列表"""
    q = db.query(ReplenishmentSuggestion)
    if status:
        q = q.filter(ReplenishmentSuggestion.status == status)
    if warehouse_id:
        q = q.filter(ReplenishmentSuggestion.warehouse_id == warehouse_id)
    if part_no:
        q = q.filter(ReplenishmentSuggestion.part_no.like(f"%{part_no}%"))

    total = q.count()
    items = q.order_by(
        ReplenishmentSuggestion.status,
        ReplenishmentSuggestion.created_at.desc(),
    ).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for s in items:
        result.append({
            "id": s.id,
            "warehouse_id": s.warehouse_id,
            "warehouse_name": s.warehouse.name if s.warehouse else None,
            "part_no": s.part_no,
            "part_name": s.part_name,
            "spec": s.spec,
            "unit": s.unit,
            "current_qty": s.current_qty,
            "reorder_point": s.reorder_point,
            "min_stock": s.min_stock,
            "avg_daily_usage": s.avg_daily_usage,
            "suggested_qty": s.suggested_qty,
            "lead_time_days": s.lead_time_days,
            "expected_arrival": s.expected_arrival.isoformat() if s.expected_arrival else None,
            "unit_cost": s.unit_cost,
            "total_cost": s.total_cost,
            "status": s.status,
            "source": s.source,
            "remark": s.remark,
            "operator": s.operator,
            "approved_by": s.approved_by,
            "approved_at": s.approved_at.isoformat() if s.approved_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })

    return {"total": total, "items": result, "page": page, "page_size": page_size}


@router.post("/replenishments", response_model=ReplenishmentSuggestionOut, status_code=201)
def create_replenishment(
    data: ReplenishmentSuggestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """手动创建补货建议"""
    wh = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id, Warehouse.is_deleted == 0).first()
    if not wh:
        raise HTTPException(404, "仓库不存在")

    total_cost = data.suggested_qty * data.unit_cost
    suggestion = ReplenishmentSuggestion(
        warehouse_id=data.warehouse_id,
        part_no=data.part_no,
        part_name=data.part_name or data.part_no,
        spec=data.spec,
        unit=data.unit,
        current_qty=data.current_qty,
        reorder_point=data.reorder_point,
        min_stock=data.min_stock,
        avg_daily_usage=data.avg_daily_usage,
        suggested_qty=data.suggested_qty,
        lead_time_days=data.lead_time_days,
        unit_cost=data.unit_cost,
        total_cost=total_cost,
        status="pending",
        source="manual",
        remark=data.remark,
        operator=data.operator or current_user.username,
    )
    db.add(suggestion)
    db.flush()
    db.commit()
    db.refresh(suggestion)
    return suggestion


@router.put("/replenishments/{rid}", response_model=ReplenishmentSuggestionOut)
def update_replenishment(
    rid: int,
    data: ReplenishmentSuggestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """更新补货建议（调整数量等）"""
    s = db.query(ReplenishmentSuggestion).filter(ReplenishmentSuggestion.id == rid).first()
    if not s:
        raise HTTPException(404, "补货建议不存在")
    if s.status != "pending":
        raise HTTPException(400, f"当前状态为 {s.status}，不可修改")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    # 重新计算总额
    s.total_cost = s.suggested_qty * s.unit_cost
    db.flush()
    db.commit()
    db.refresh(s)
    return s


@router.patch("/replenishments/{rid}/status")
def update_replenishment_status(
    rid: int,
    status: str = Query(..., pattern="^(approved|purchased|cancelled)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """更新补货建议状态

    flow: pending → approved → purchased
                       → cancelled
    """
    s = db.query(ReplenishmentSuggestion).filter(ReplenishmentSuggestion.id == rid).first()
    if not s:
        raise HTTPException(404, "补货建议不存在")

    valid_transitions = {
        "pending": ["approved", "cancelled"],
        "approved": ["purchased", "cancelled"],
        "purchased": [],
        "cancelled": [],
    }
    if status not in valid_transitions.get(s.status, []):
        raise HTTPException(400, f"不允许从 {s.status} 变更为 {status}")

    s.status = status
    if status == "approved":
        s.approved_by = current_user.username
        s.approved_at = datetime.utcnow()
        # 自动解析相关预警
        alerts = db.query(Alert).filter(
            Alert.target_type == "inventory",
            Alert.target_id.in_(
                db.query(Inventory.id).filter(
                    Inventory.part_no == s.part_no,
                    Inventory.warehouse_id == s.warehouse_id,
                )
            ),
            Alert.is_resolved == False,
        ).all()
        for a in alerts:
            a.is_resolved = True
            a.resolved_by = current_user.username
            a.resolved_at = datetime.utcnow()

    db.commit()
    return {"message": f"补货建议已变更为 {status}", "status": status}


@router.get("/replenishments/stats", response_model=ReplenishmentStatsOut)
def replenishment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("inventory")),
):
    """补货建议统计概览"""
    pending = db.query(ReplenishmentSuggestion).filter(
        ReplenishmentSuggestion.status == "pending"
    ).count()
    approved = db.query(ReplenishmentSuggestion).filter(
        ReplenishmentSuggestion.status == "approved"
    ).count()
    purchased = db.query(ReplenishmentSuggestion).filter(
        ReplenishmentSuggestion.status == "purchased"
    ).count()

    total_qty = db.query(
        func.coalesce(func.sum(ReplenishmentSuggestion.suggested_qty), 0)
    ).filter(
        ReplenishmentSuggestion.status.in_(["pending", "approved"])
    ).scalar() or 0

    total_cost = db.query(
        func.coalesce(func.sum(ReplenishmentSuggestion.total_cost), 0)
    ).filter(
        ReplenishmentSuggestion.status.in_(["pending", "approved"])
    ).scalar() or 0

    urgent = db.query(ReplenishmentSuggestion).filter(
        ReplenishmentSuggestion.status == "pending",
        ReplenishmentSuggestion.current_qty <= ReplenishmentSuggestion.min_stock,
        ReplenishmentSuggestion.min_stock > 0,
    ).count()

    return ReplenishmentStatsOut(
        pending_count=pending,
        approved_count=approved,
        purchased_count=purchased,
        total_suggested_qty=float(total_qty),
        total_cost=float(total_cost),
        urgent_count=urgent,
    )
