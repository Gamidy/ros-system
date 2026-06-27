"""预警/通知管理 API"""
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.user import User
from app.models.alert import Notification, Alert, AlertRule
from app.models.project import Project
from app.models.test import TestRequest, Certification
from app.models.notification_read import NotificationReadStatus, CHANNEL_TYPES
from app.schemas import (
    NotificationOut, AlertOut, AlertRuleOut,
    NotificationPageOut, BatchDeleteRequest,
)
from app.services.events import bus, EventTypes

router = APIRouter(prefix="", tags=["预警/通知管理"])


# ═══════════════ 通知管理 ═══════════════


def _enrich_notification_with_read_status(
    notif: Notification,
    current_username: str,
    db: Session,
) -> dict:
    """为单条通知附加跨渠道已读状态

    查询 NotificationReadStatus 表，获取当前用户在所有渠道上的已读标记。
    """
    notif_dict = {
        "id": notif.id,
        "alert_id": notif.alert_id,
        "target_user": notif.target_user,
        "channel": notif.channel,
        "title": notif.title,
        "content": notif.content,
        "is_sent": notif.is_sent,
        "is_read": notif.is_read,
        "sent_at": notif.sent_at,
        "read_at": notif.read_at,
        "created_at": notif.created_at,
        "cross_channel_read": None,
    }

    # 查询跨渠道已读状态
    read_statuses = (
        db.query(NotificationReadStatus)
        .filter(
            NotificationReadStatus.notification_id == str(notif.id),
            NotificationReadStatus.user_id == current_username,
        )
        .all()
    )

    if read_statuses:
        cross_channel: dict[str, Optional[datetime]] = {}
        for ct in CHANNEL_TYPES:
            cross_channel[ct] = None
        for rs in read_statuses:
            cross_channel[rs.channel_type] = rs.read_at
        notif_dict["cross_channel_read"] = cross_channel

    return notif_dict


@router.get("/notifications", response_model=NotificationPageOut)
def list_notifications(
    target_user: str = Query("", description="目标用户"),
    is_read: Optional[bool] = Query(None, description="是否已读"),
    channel: str = Query("", description="通知渠道"),
    keyword: str = Query("", description="搜索关键词（匹配标题和内容）"),
    date_from: Optional[datetime] = Query(None, description="起始时间 (ISO格式)"),
    date_to: Optional[datetime] = Query(None, description="结束时间 (ISO格式)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("alerts")),
) -> NotificationPageOut:
    """获取通知列表（分页），含跨渠道已读状态

    支持按 target_user / is_read / channel / keyword / date range 筛选。
    返回 NotificationPageOut 分页结构。
    """
    q = db.query(Notification)
    if target_user:
        q = q.filter(Notification.target_user == target_user)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    if channel:
        q = q.filter(Notification.channel == channel)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(Notification.title.ilike(kw), Notification.content.ilike(kw))
        )
    if date_from:
        q = q.filter(Notification.created_at >= date_from)
    if date_to:
        q = q.filter(Notification.created_at <= date_to)

    total: int = q.count()
    items = (
        q.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    current_username = str(current_user.username)
    enriched = [
        _enrich_notification_with_read_status(n, current_username, db)
        for n in items
    ]

    return NotificationPageOut(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.patch("/notifications/{nid}/read")
def mark_notification_read(
    nid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "project_admin", "procurement", "quality_engineer", "finance_manager", "product_manager", "process_engineer", "production", "security_officer")),
) -> dict:
    notif = db.query(Notification).filter(Notification.id == nid).first()
    if not notif:
        raise HTTPException(status_code=404, detail="通知记录不存在")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.delete("/notifications/batch")
def delete_notifications_batch(
    body: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("alerts")),
) -> dict:
    """批量删除通知"""
    deleted: int = 0
    for nid in body.ids:
        notif = db.query(Notification).filter(Notification.id == nid).first()
        if notif:
            db.delete(notif)
            deleted += 1
    db.commit()
    return {"ok": True, "deleted_count": deleted}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("alerts")),
) -> dict:
    """全部标记已读"""
    now = datetime.now(timezone.utc)
    count: int = (
        db.query(Notification)
        .filter(
            Notification.target_user == str(current_user.username),
            Notification.is_read == False,
        )
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "updated_count": count}


# ═══════════════ 预警记录 ═══════════════

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    is_read: bool = Query(None, description="是否已读"),
    level: int = Query(None, description="预警级别: 1紧急/2警告/3提示"),
    alert_type: str = Query("", description="预警类型"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
) -> list[AlertOut]:
    """获取预警记录列表，支持按 is_read / level / alert_type 筛选"""
    q = db.query(Alert)
    if is_read is not None:
        q = q.filter(Alert.is_read == is_read)
    if level is not None:
        q = q.filter(Alert.level == level)
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    return q.order_by(Alert.created_at.desc()).limit(200).all()


# ═══════════════ 预警规则 ═══════════════

@router.get("/alert-rules", response_model=list[AlertRuleOut])
def list_alert_rules(
    is_enabled: bool = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
) -> list[AlertRuleOut]:
    """获取预警规则列表，支持按 is_enabled 筛选"""
    q = db.query(AlertRule)
    if is_enabled is not None:
        q = q.filter(AlertRule.is_enabled == is_enabled)
    return q.order_by(AlertRule.created_at.desc()).all()


# ═══════════════ 超期检查 ═══════════════

@router.post("/alerts/check-overdue")
def check_overdue(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "project_admin", "procurement", "quality_engineer", "finance_manager", "product_manager", "process_engineer", "production", "security_officer")),
) -> dict:
    """检查超期项目/认证/测试，自动创建 overdue 预警记录"""
    today = date.today()
    created_count = 0
    alerts_created = []

    # 1. 检查超期项目 (target_end_date 已过但状态仍为 running/planning)
    overdue_projects = db.query(Project).filter(
        Project.target_end_date.isnot(None),
        Project.target_end_date < today,
        Project.status.in_(["planning", "running"]),
        Project.is_deleted == False,
    ).all()

    for proj in overdue_projects:
        existing = db.query(Alert).filter(
            Alert.target_type == "project",
            Alert.target_id == proj.id,
            Alert.alert_type == "overdue",
            Alert.is_resolved == False,
        ).first()
        if not existing:
            alert = Alert(
                target_type="project",
                target_id=proj.id,
                title=f"项目超期: {proj.name}",
                level=1,
                alert_type="overdue",
                message=f"项目 [{proj.code}] {proj.name} 目标完成日期 {proj.target_end_date} 已过期，当前状态: {proj.status}",
            )
            db.add(alert)
            created_count += 1
            alerts_created.append({
                "target_type": "project",
                "target_id": proj.id,
                "title": alert.title,
                "level": alert.level,
            })
            db.flush()  # 先flush让alert.id有值再emit
            bus.emit(EventTypes.ALERT_OVERDUE_FOUND, alert_id=alert.id, target_type="project", target_id=proj.id, title=alert.title, level=alert.level, message=alert.message)

    # 2. 检查超期测试 (target_date 已过但状态仍为 draft/submitted/testing)
    overdue_tests = db.query(TestRequest).filter(
        TestRequest.target_date.isnot(None),
        TestRequest.target_date < today,
        TestRequest.status.in_(["draft", "submitted", "testing"]),
    ).all()

    for test in overdue_tests:
        existing = db.query(Alert).filter(
            Alert.target_type == "test",
            Alert.target_id == test.id,
            Alert.alert_type == "overdue",
            Alert.is_resolved == False,
        ).first()
        if not existing:
            alert = Alert(
                target_type="test",
                target_id=test.id,
                title=f"测试超期: {test.title}",
                level=2,
                alert_type="overdue",
                message=f"测试 [{test.request_no}] {test.title} 目标日期 {test.target_date} 已过期，当前状态: {test.status}",
            )
            db.add(alert)
            created_count += 1
            alerts_created.append({
                "target_type": "test",
                "target_id": test.id,
                "title": alert.title,
                "level": alert.level,
            })
            db.flush()
            bus.emit(EventTypes.ALERT_OVERDUE_FOUND, alert_id=alert.id, target_type="test", target_id=test.id, title=alert.title, level=alert.level, message=alert.message)

    # 3. 检查超期认证
    overdue_certs = db.query(Certification).filter(
        Certification.planned_date.isnot(None),
        Certification.planned_date < today,
        Certification.status.in_(["planning", "preparing", "testing", "submitted"]),
    ).all()

    for cert in overdue_certs:
        existing = db.query(Alert).filter(
            Alert.target_type == "certification",
            Alert.target_id == cert.id,
            Alert.alert_type == "overdue",
            Alert.is_resolved == False,
        ).first()
        if not existing:
            alert = Alert(
                target_type="certification",
                target_id=cert.id,
                title=f"认证超期: {cert.cert_type}",
                level=2,
                alert_type="overdue",
                message=f"认证 [{cert.cert_no}] {cert.cert_type} ({cert.target_market}) 计划日期 {cert.planned_date} 已过期，当前状态: {cert.status}",
            )
            db.add(alert)
            created_count += 1
            alerts_created.append({
                "target_type": "certification",
                "target_id": cert.id,
                "title": alert.title,
                "level": alert.level,
            })
            db.flush()
            bus.emit(EventTypes.ALERT_OVERDUE_FOUND, alert_id=alert.id, target_type="certification", target_id=cert.id, title=alert.title, level=alert.level, message=alert.message)

    if created_count > 0:
        db.commit()

    return {
        "ok": True,
        "created_count": created_count,
        "alerts": alerts_created,
    }
