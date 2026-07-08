"""项目管理API — Gate节点管理"""
from datetime import date
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, require_menu
from app.models.project import Project, ProjectGate
from app.api.projects import _get_gate_template, _validate_gate_transition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["项目管理-Gate"])


@router.get("/{pid}/gates")
def list_gates(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> list:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    gates = db.query(ProjectGate).filter(ProjectGate.project_id == pid).order_by(ProjectGate.seq).all()
    return [{"id": g.id, "project_id": g.project_id, "gate_code": g.gate_code,
             "gate_name": g.gate_name, "seq": g.seq, "decision_level": g.decision_level,
             "pass_conditions": g.pass_conditions, "is_high_risk_zone": g.is_high_risk_zone,
             "is_hidden": g.is_hidden, "status": g.status,
             "planned_date": g.planned_date.isoformat() if g.planned_date else None,
             "actual_date": g.actual_date.isoformat() if g.actual_date else None,
             "decision": g.decision, "reviewer": g.reviewer,
             "created_at": g.created_at.isoformat() if g.created_at else None} for g in gates]


@router.post("/{pid}/gates")
def create_gate(
    pid: int, gate_code: str, gate_name: str, seq: int,
    decision_level: str | None = None, pass_conditions: str | None = None,
    planned_date: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if db.query(ProjectGate).filter(ProjectGate.project_id == pid, ProjectGate.gate_code == gate_code).first():
        raise HTTPException(status_code=400, detail=f"Gate {gate_code} 已存在")
    g = ProjectGate(project_id=pid, gate_code=gate_code, gate_name=gate_name, seq=seq,
                    decision_level=decision_level, pass_conditions=pass_conditions, planned_date=planned_date)
    db.add(g); db.commit(); db.refresh(g)
    return g


@router.post("/{pid}/gates/bulk")
def bulk_create_gates(
    pid: int, db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    """根据项目等级自动生成全部M1~M9 Gate"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    template = _get_gate_template(p.project_class)
    existing = {g.gate_code: g for g in db.query(ProjectGate).filter(ProjectGate.project_id == pid).all()}
    created, skipped = [], []
    for gate_def in template:
        code = gate_def["code"]
        if code in existing:
            skipped.append(code); continue
        db.add(ProjectGate(project_id=pid, gate_code=code, gate_name=gate_def["name"],
                seq=gate_def["seq"], decision_level=gate_def["decision_level"],
                is_high_risk_zone=gate_def["is_high_risk_zone"],
                is_hidden=gate_def["is_hidden"]))
        created.append(code)
    db.commit()
    return {"created": created, "skipped": skipped, "total": len(created)}


@router.patch("/{pid}/gates/{gate_code}")
def update_gate_status(
    pid: int, gate_code: str, status: str,
    actual_date: date | None = None, decision: str | None = None,
    reviewer: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    gate = db.query(ProjectGate).filter(ProjectGate.project_id == pid, ProjectGate.gate_code == gate_code).first()
    if not gate:
        raise HTTPException(status_code=404, detail=f"Gate {gate_code} 不存在")
    _validate_gate_transition(pid, gate_code, status, db)
    gate.status = status
    if actual_date:
        gate.actual_date = actual_date
    elif status == "passed":
        gate.actual_date = date.today()
    if decision:
        gate.decision = decision
    if reviewer:
        gate.reviewer = reviewer
    db.commit(); db.refresh(gate)
    return {"id": gate.id, "project_id": gate.project_id, "gate_code": gate.gate_code,
            "gate_name": gate.gate_name, "seq": gate.seq, "decision_level": gate.decision_level,
            "pass_conditions": gate.pass_conditions, "is_high_risk_zone": gate.is_high_risk_zone,
            "is_hidden": gate.is_hidden, "status": gate.status,
            "planned_date": gate.planned_date.isoformat() if gate.planned_date else None,
            "actual_date": gate.actual_date.isoformat() if gate.actual_date else None,
            "decision": gate.decision, "ok": True}
