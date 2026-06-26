"""认证门禁规则 API — Phase 6 S2

标准 CRUD（GET/POST/PUT/DELETE）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.cert_gate_rule import CertificationGateRule
from app.schemas import CertificationGateRuleCreate, CertificationGateRuleUpdate, CertificationGateRuleOut

router = APIRouter(prefix="/api/s2/gate-rules", tags=["S2-认证门禁规则"])


@router.get("", response_model=list[CertificationGateRuleOut])
def list_gate_rules(
    gate_code: str = Query("", description="按门禁编号筛选"),
    cert_type: str = Query("", description="按认证类型筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-gate-rules")),
) -> list[CertificationGateRuleOut]:
    """认证门禁规则列表"""
    q = db.query(CertificationGateRule)
    if gate_code:
        q = q.filter(CertificationGateRule.gate_code == gate_code)
    if cert_type:
        q = q.filter(CertificationGateRule.cert_type == cert_type)
    return q.order_by(CertificationGateRule.priority, CertificationGateRule.created_at.desc()).all()


@router.post("", response_model=CertificationGateRuleOut, status_code=201)
def create_gate_rule(
    data: CertificationGateRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("cert-gate-rules")),
) -> CertificationGateRuleOut:
    """创建认证门禁规则"""
    rule = CertificationGateRule(
        **data.model_dump(exclude_unset=True),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=CertificationGateRuleOut)
def get_gate_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-gate-rules")),
) -> CertificationGateRuleOut:
    """认证门禁规则详情"""
    rule = db.query(CertificationGateRule).filter(CertificationGateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="门禁规则不存在")
    return rule


@router.put("/{rule_id}", response_model=CertificationGateRuleOut)
def update_gate_rule(
    rule_id: int,
    data: CertificationGateRuleUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-gate-rules")),
) -> CertificationGateRuleOut:
    """更新认证门禁规则"""
    rule = db.query(CertificationGateRule).filter(CertificationGateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="门禁规则不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, val)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}")
def delete_gate_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-gate-rules")),
) -> dict:
    """删除认证门禁规则"""
    rule = db.query(CertificationGateRule).filter(CertificationGateRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="门禁规则不存在")
    db.delete(rule)
    db.commit()
    return {"success": True, "message": "门禁规则已删除"}
