"""预警/通知管理 API"""
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.user import User
from app.models.alert import Notification, Alert, AlertRule
from app.models.project import Project
from app.models.test import TestRequest, Certification
from app.schemas import NotificationOut, AlertOut, AlertRuleOut

router = APIRouter(prefix="", tags=["预警/通知管理"])


# ═══════════════ 通知管理 ═══════════════

@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    target_user: str = Query("", description="目标用户"),
    is_read: bool = Query(None, description="是否已读"),
    channel: str = Query("", description="通知渠道"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
):
    q = db.query(Notification)
    if target_user:
        q = q.filter(Notification.target_user == target_user)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    if channel:
        q = q.filter(Notification.channel == channel)
    return q.order_by(Notification.created_at.desc()).limit(200).all()


@router.patch("/notifications/{nid}/read")
def mark_notification_read(
    nid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "project_admin", "procurement", "quality_engineer", "finance_manager", "product_manager", "process_engineer", "production", "security_officer")),
):
    notif = db.query(Notification).filter(Notification.id == nid).first()
    if not notif:
        raise HTTPException(status_code=404, detail="通知记录不存在")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ═══════════════ 预警记录 ═══════════════

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    is_read: bool = Query(None, description="是否已读"),
    level: int = Query(None, description="预警级别: 1紧急/2警告/3提示"),
    alert_type: str = Query("", description="预警类型"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
):
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
):
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
):
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

    if created_count > 0:
        db.commit()

    return {
        "ok": True,
        "created_count": created_count,
        "alerts": alerts_created,
    }
