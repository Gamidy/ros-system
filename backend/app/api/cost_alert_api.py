"""成本超标预警引擎 — CRUD API

RESTful 端点:
  GET/POST   /api/cost-alert-rules
  PUT/DELETE /api/cost-alert-rules/{id}
  GET        /api/cost-alert-events
  POST       /api/cost-alert-events/check   ← 手动触发检查
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import require_menu
from app.models.cost_alert_rule import CostAlertRule, AlertEvent
from app.services.cost_alert_service import check_cost_alerts

router = APIRouter(prefix="/cost-alert-rules", tags=["成本超标预警引擎"])


# ── Schemas ──────────────────────────────────────────────────────────

class CostAlertRuleCreate(BaseModel):
    name: str = Field(..., max_length=100, description="规则名称")
    threshold_pct: float = Field(0, description="超标百分比阈值")
    threshold_amount: float = Field(0, description="超标金额阈值(元)")
    project_type: Optional[str] = Field(None, max_length=50, description="适用产品类型")
    enabled: bool = Field(True, description="是否启用")


class CostAlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    threshold_pct: Optional[float] = None
    threshold_amount: Optional[float] = None
    project_type: Optional[str] = Field(None, max_length=50)
    enabled: Optional[bool] = None


class CostAlertRuleOut(BaseModel):
    id: int
    name: str
    threshold_pct: float
    threshold_amount: float
    project_type: Optional[str]
    enabled: bool
    org_id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class AlertEventOut(BaseModel):
    id: int
    rule_id: int
    rule_name: str
    sheet_id: int
    product_plan_id: str
    plan_name: Optional[str]
    target_amount: float
    actual_amount: float
    variance_amount: float
    variance_pct: float
    threshold_pct: float
    threshold_amount: float
    alert_level: str
    message: Optional[str]
    is_read: bool
    is_resolved: bool
    resolved_at: Optional[str]
    org_id: Optional[int]
    created_at: Optional[str]

    class Config:
        from_attributes = True


# ── 规则 CRUD ──────────────────────────────────────────────────────────

@router.get("", response_model=list[CostAlertRuleOut])
def list_rules(
    enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """获取成本超标预警规则列表"""
    q = db.query(CostAlertRule)
    if enabled is not None:
        q = q.filter(CostAlertRule.enabled == enabled)
    return q.order_by(desc(CostAlertRule.created_at)).all()


@router.post("", response_model=CostAlertRuleOut, status_code=201)
def create_rule(
    body: CostAlertRuleCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """创建成本超标预警规则"""
    rule = CostAlertRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=CostAlertRuleOut)
def update_rule(
    rule_id: int,
    body: CostAlertRuleUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """更新成本超标预警规则"""
    rule = db.query(CostAlertRule).filter(CostAlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """删除成本超标预警规则"""
    rule = db.query(CostAlertRule).filter(CostAlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    db.delete(rule)
    db.commit()
    return None


# ── 事件查询 & 手动触发 ────────────────────────────────────────────────

@router.get("/events", response_model=list[AlertEventOut])
def list_events(
    rule_id: Optional[int] = Query(None, description="按规则ID筛选"),
    alert_level: Optional[str] = Query(None, description="按等级筛选: warning/critical"),
    is_resolved: Optional[bool] = Query(None, description="按处理状态筛选"),
    limit: int = Query(50, ge=1, le=500, description="返回条数"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """获取成本超标事件列表（按创建时间倒序）"""
    q = db.query(AlertEvent)
    if rule_id is not None:
        q = q.filter(AlertEvent.rule_id == rule_id)
    if alert_level is not None:
        q = q.filter(AlertEvent.alert_level == alert_level)
    if is_resolved is not None:
        q = q.filter(AlertEvent.is_resolved == is_resolved)
    return q.order_by(desc(AlertEvent.created_at)).limit(limit).all()


@router.post("/events/check")
def trigger_check(
    db: Session = Depends(get_db),
    _=Depends(require_menu("bi-analytics")),
):
    """手动触发成本超标检查"""
    new_events = check_cost_alerts(db)
    return {
        "checked": True,
        "new_events_count": len(new_events),
        "new_events": [
            {
                "id": e.id,
                "rule_name": e.rule_name,
                "plan_name": e.plan_name,
                "variance_pct": e.variance_pct,
                "alert_level": e.alert_level,
            }
            for e in new_events
        ],
    }
