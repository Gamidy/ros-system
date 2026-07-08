"""驾驶舱仪表盘 — 预警管理 API"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.alert import Alert, AlertRule
from app.schemas import (
    AlertOut,
    AlertRuleCreate,
    AlertRuleOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱-预警管理"])


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    level: int = Query(None, description="预警级别: 1紧急/2警告/3提示"),
    is_resolved: bool = Query(None, description="是否已解决"),
    alert_type: str = Query("", description="预警类型"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
) -> list[AlertOut]:
    """列出预警记录，支持级别/状态/类型筛选"""
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
    _=Depends(require_role(
        "admin", "general_manager", "rd_director", "project_admin",
        "product_manager", "quality_engineer",
    )),
) -> dict:
    """标记预警为已解决"""
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
    _=Depends(require_menu("alerts")),
) -> list[AlertRuleOut]:
    """列出预警规则，支持类型/启用状态筛选"""
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
) -> AlertRuleOut:
    """创建预警规则"""
    existing = db.query(AlertRule).filter(AlertRule.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"规则[{data.name}]已存在")
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
