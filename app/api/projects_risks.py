"""项目管理API — 风险 & 延期传导链预警"""
from datetime import date
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role, require_menu
from app.models.user import User
from app.models.project import Project, Milestone, Risk
from app.schemas import RiskCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["项目管理-风险"])


# ══════════════════════════════════════════════════════════════
# Delay Chain Warning (延期传导链预警)
# ══════════════════════════════════════════════════════════════

@router.get("/{pid}/delay-chain")
def get_delay_chain(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> dict:
    """延期传导链预警: 计算里程碑依赖链的延期放大效应"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    milestones = db.query(Milestone).filter(Milestone.project_id == pid).all()
    if not milestones:
        return {"project_id": pid, "project_name": p.name, "chains": [], "overall_amplification": None}
    milestone_map: dict[int, Milestone] = {m.id: m for m in milestones}
    delays: dict[int, int] = {}
    for m in milestones:
        if m.actual_date and m.planned_date:
            d = (m.actual_date - m.planned_date).days
            if d > 0:
                delays[m.id] = d
    downstream_map: dict[int, list[int]] = {}
    for m in milestones:
        if m.depends_on_milestone_id and m.depends_on_milestone_id in milestone_map:
            upstream_id = m.depends_on_milestone_id
            downstream_map.setdefault(upstream_id, []).append(m.id)
    DEFAULT_AMPLIFICATION = 1.5

    def walk_chain(upstream_id: int, accumulated_amplification: float, visited: set) -> list[dict]:
        impacts = []
        if upstream_id not in downstream_map:
            return impacts
        for down_id in downstream_map[upstream_id]:
            if down_id in visited:
                continue
            down_m = milestone_map[down_id]
            if upstream_id in delays and down_id in delays:
                edge_amp = delays[down_id] / max(delays[upstream_id], 1)
            else:
                edge_amp = DEFAULT_AMPLIFICATION
            total_amp = round(accumulated_amplification * edge_amp, 2)
            estimated_impact = round(delays.get(upstream_id, 0) * total_amp)
            new_visited = visited | {down_id}
            impact_entry = {"downstream_milestone": down_m.name,
                            "downstream_milestone_id": down_m.id,
                            "amplification": total_amp,
                            "estimated_impact_days": estimated_impact,
                            "downstream_delay_days": delays.get(down_id, None),
                            "downstream_status": down_m.status}
            sub_impacts = walk_chain(down_id, total_amp, new_visited)
            if sub_impacts:
                impact_entry["further_impacts"] = sub_impacts
            impacts.append(impact_entry)
        return impacts

    chains = []
    for m in milestones:
        if m.id in delays:
            impact_list = walk_chain(m.id, 1.0, {m.id})
            if impact_list:
                chains.append({"milestone": m.name, "milestone_id": m.id,
                               "delay_days": delays[m.id],
                               "planned_date": str(m.planned_date) if m.planned_date else None,
                               "actual_date": str(m.actual_date) if m.actual_date else None,
                               "impacts": impact_list})
    overall_amplification = None
    if chains:
        all_impacts = [imp["amplification"] for chain in chains for imp in chain["impacts"]]
        if all_impacts:
            overall_amplification = round(max(all_impacts), 2)
    return {"project_id": pid, "project_name": p.name, "project_class": p.project_class,
            "total_milestones": len(milestones), "delayed_milestones": len(delays),
            "chains": chains, "overall_amplification": overall_amplification}


# ══════════════════════════════════════════════════════════════
# Risk Management
# ══════════════════════════════════════════════════════════════

@router.get("/{pid}/risks")
def list_risks(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> list:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return db.query(Risk).filter(Risk.project_id == pid).order_by(Risk.created_at.desc()).all()


@router.post("/{pid}/risks")
def create_risk(
    pid: int, req: RiskCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if req.risk_level not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="风险等级须为A/B/C")
    if req.probability not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="无效概率")
    if req.impact not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="无效影响度")
    r = Risk(project_id=pid, title=req.title, risk_level=req.risk_level,
             risk_source=req.risk_source, probability=req.probability,
             impact=req.impact, mitigation=req.mitigation)
    db.add(r); db.commit(); db.refresh(r)
    return r


@router.patch("/{pid}/risks/{rid}")
def update_risk(
    pid: int, rid: int,
    status: str | None = None, mitigation: str | None = None,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    r = db.query(Risk).filter(Risk.id == rid, Risk.project_id == pid).first()
    if not r:
        raise HTTPException(status_code=404, detail="风险不存在")
    if status:
        if status not in ("open", "monitoring", "resolved"):
            raise HTTPException(status_code=400, detail="无效状态")
        r.status = status
        if status == "resolved":
            r.resolved_at = date.today()
    if mitigation is not None:
        r.mitigation = mitigation
    if risk_level:
        if risk_level not in ("A", "B", "C"):
            raise HTTPException(status_code=400, detail="风险等级须为A/B/C")
        r.risk_level = risk_level
    db.commit(); db.refresh(r)
    return r
