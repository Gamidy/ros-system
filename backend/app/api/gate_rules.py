"""Gate规则引擎 API — Phase 6 S1"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.gate_rule import GateRule, GateRuleItem, GateEvalRecord
from app.schemas import (
    GateRuleCreate, GateRuleOut,
    GateRuleItemOut,
    GateRuleEvalRequest,
)
from app.services.gate_rule_engine import GateRuleEngine

router = APIRouter(prefix="/api/gate-rules", tags=["Gate规则引擎"])


@router.get("", response_model=list[GateRuleOut])
def list_gate_rules(
    gate_code: str = Query("", description="Gate编号"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    q = db.query(GateRule)
    if gate_code:
        q = q.filter(GateRule.gate_code == gate_code)
    if status:
        q = q.filter(GateRule.status == status)
    return q.order_by(GateRule.priority).all()


@router.post("", response_model=GateRuleOut)
def create_gate_rule(
    data: GateRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("tests")),
):
    items_data = data.items
    rule_data = data.model_dump(exclude={"items"})
    rule = GateRule(
        **rule_data,
        status="active",
        created_by=getattr(current_user, "username", None),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(rule)
    db.flush()

    for item_data in items_data:
        item = GateRuleItem(rule_id=rule.id, **item_data.model_dump())
        db.add(item)

    db.commit()
    db.refresh(rule)
    return rule


@router.get("/{rid}", response_model=GateRuleOut)
def get_gate_rule(
    rid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    rule = db.query(GateRule).filter(GateRule.id == rid).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Gate规则不存在")
    return rule


@router.put("/{rid}", response_model=GateRuleOut)
def update_gate_rule(
    rid: int,
    data: GateRuleCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    rule = db.query(GateRule).filter(GateRule.id == rid).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Gate规则不存在")

    items_data = data.items
    rule_data = data.model_dump(exclude={"items"})

    for key, val in rule_data.items():
        setattr(rule, key, val)
    rule.updated_at = datetime.now(timezone.utc)
    db.flush()

    # 重建 items
    db.query(GateRuleItem).filter(GateRuleItem.rule_id == rid).delete()
    for item_data in items_data:
        item = GateRuleItem(rule_id=rid, **item_data.model_dump())
        db.add(item)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rid}")
def delete_gate_rule(
    rid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    rule = db.query(GateRule).filter(GateRule.id == rid).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Gate规则不存在")
    db.delete(rule)
    db.commit()
    return {"ok": True, "message": "Gate规则已删除"}


@router.patch("/{rid}/status")
def patch_gate_rule_status(
    rid: int,
    status: str = Query(..., description="目标状态 active/inactive"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    rule = db.query(GateRule).filter(GateRule.id == rid).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Gate规则不存在")
    rule.status = status
    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": rule.status}


@router.post("/evaluate")
def evaluate_gate_rule(
    data: GateRuleEvalRequest,
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    """评估Gate规则 — 使用 GateRuleEngine"""
    engine = GateRuleEngine(db)
    result = engine.evaluate(
        project_id=data.project_id,
        gate_code=data.gate_code,
        product_line=data.product_line,
        customer=data.customer,
    )
    return result
