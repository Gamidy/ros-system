"""驾驶舱仪表盘 API"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import Product
from app.models.project import Project, ProjectGate
from app.models.bom import Part
from app.models.test import TestRequest, Certification, QualityIssue
from app.models.alert import Alert, AlertRule
from app.schemas import (
    DashboardSummary,
    AlertOut,
    AlertRuleCreate,
    AlertRuleOut,
)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱"])


# ═══════════════ 驾驶舱汇总 ═══════════════

@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    ninety_days = today + __import__("datetime").timedelta(days=90)

    total_products = db.query(func.count(Product.id)).scalar() or 0
    active_projects = db.query(func.count(Project.id)).filter(
        Project.status == "running"
    ).scalar() or 0

    # 高风险项目：M4/M5/M6 Gate 处于高风险区且未通过
    high_risk_gates = db.query(func.count(func.distinct(ProjectGate.project_id))).filter(
        ProjectGate.gate_code.in_(["M4", "M5", "M6"]),
        ProjectGate.is_high_risk_zone == True,
        ProjectGate.status != "passed",
    ).scalar() or 0
    high_risk_projects = high_risk_gates

    pending_tests = db.query(func.count(TestRequest.id)).filter(
        TestRequest.status.in_(["draft", "submitted"])
    ).scalar() or 0

    active_certifications = db.query(func.count(Certification.id)).filter(
        Certification.status.notin_(["approved", "rejected", "expiring"])
    ).scalar() or 0

    open_quality_issues = db.query(func.count(QualityIssue.id)).filter(
        QualityIssue.status != "closed"
    ).scalar() or 0

    unresolved_alerts = db.query(func.count(Alert.id)).filter(
        Alert.is_resolved == False
    ).scalar() or 0

    cdf_expiring_soon = db.query(func.count(Part.id)).filter(
        Part.cdf_expiry_date.isnot(None),
        Part.cdf_expiry_date <= ninety_days,
        Part.cdf_expiry_date >= today,
    ).scalar() or 0

    # M4/M5/M6 高风险Gate的项目数
    m4_m6_at_risk = db.query(func.count(func.distinct(ProjectGate.project_id))).filter(
        ProjectGate.gate_code.in_(["M4", "M5", "M6"]),
        ProjectGate.is_high_risk_zone == True,
        ProjectGate.status == "pending",
    ).scalar() or 0

    return DashboardSummary(
        total_products=total_products,
        active_projects=active_projects,
        high_risk_projects=high_risk_projects,
        pending_tests=pending_tests,
        active_certifications=active_certifications,
        open_quality_issues=open_quality_issues,
        unresolved_alerts=unresolved_alerts,
        cdf_expiring_soon=cdf_expiring_soon,
        m4_m6_at_risk=m4_m6_at_risk,
    )


# ═══════════════ 预警管理 ═══════════════

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    level: int = Query(None, description="预警级别: 1紧急/2警告/3提示"),
    is_resolved: bool = Query(None, description="是否已解决"),
    alert_type: str = Query("", description="预警类型"),
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if level is not None:
        q = q.filter(Alert.level == level)
    if is_resolved is not None:
        q = q.filter(Alert.is_resolved == is_resolved)
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    return q.order_by(Alert.level.desc(), Alert.created_at.desc()).all()


@router.patch("/alerts/{aid}")
def resolve_alert(
    aid: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    alert = db.query(Alert).filter(Alert.id == aid).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ═══════════════ 预警规则 ═══════════════

@router.get("/alerts/rules", response_model=list[AlertRuleOut])
def list_alert_rules(
    target_type: str = Query("", description="监控对象类型"),
    is_enabled: bool = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
):
    q = db.query(AlertRule)
    if target_type:
        q = q.filter(AlertRule.target_type == target_type)
    if is_enabled is not None:
        q = q.filter(AlertRule.is_enabled == is_enabled)
    return q.order_by(AlertRule.created_at.desc()).all()


@router.post("/alerts/rules", response_model=AlertRuleOut)
def create_alert_rule(
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    # check duplicate name
    existing = db.query(AlertRule).filter(AlertRule.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"规则[{data.name}]已存在")
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
