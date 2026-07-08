"""项目管理API — 项目仪表盘 & 甘特图 & 对比 & 导出"""
from datetime import date, datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from app.core.database import get_db
from app.core.security import require_menu, get_current_user
from app.models.user import User
from app.models.project import Project, ProjectGate, Task, Milestone, Risk, TaskDependency, TaskComment, TimeEntry
from app.models.product import Product
from app.models.bom import BOM
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["项目管理-仪表盘"])


# ══════════════════════════════════════════════════════════════
# Gantt 甘特图
# ══════════════════════════════════════════════════════════════

@router.get("/{pid}/gantt")
def project_gantt_data(
    pid: int, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("projects")),
) -> dict:
    """返回项目甘特图数据"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    tasks = db.query(Task).filter(Task.project_id == pid).order_by(Task.planned_date, Task.due_date).all()
    milestones = db.query(Milestone).filter(Milestone.project_id == pid).order_by(Milestone.planned_date, Milestone.actual_date).all()
    gates = db.query(ProjectGate).filter(ProjectGate.project_id == pid).order_by(ProjectGate.seq).all()
    return {
        "project": {"id": p.id, "code": p.code, "name": p.name, "project_class": p.project_class,
                     "status": p.status, "start_date": str(p.start_date) if p.start_date else None,
                     "target_end_date": str(p.target_end_date) if p.target_end_date else None},
        "tasks": [{"id": t.id, "title": t.title, "assignee": t.assignee, "status": t.status,
                    "priority": t.priority, "start_date": str(t.planned_date) if t.planned_date else str(t.created_at.date()),
                    "end_date": str(t.due_date) if t.due_date else None,
                    "actual_date": str(t.actual_date) if t.actual_date else None,
                    "milestone_id": t.milestone_id} for t in tasks],
        "milestones": [{"id": m.id, "name": m.name, "status": m.status,
                         "planned_date": str(m.planned_date) if m.planned_date else None,
                         "actual_date": str(m.actual_date) if m.actual_date else None,
                         "gate_code": m.gate_code} for m in milestones],
        "gates": [{"code": g.gate_code, "name": g.gate_name, "status": g.status, "seq": g.seq,
                    "planned_date": str(g.planned_date) if g.planned_date else None,
                    "actual_date": str(g.actual_date) if g.actual_date else None} for g in gates],
        "date_range": {"start": str(p.start_date) if p.start_date else None,
                        "end": str(p.target_end_date) if p.target_end_date else None},
        "dependencies": [{"task_id": d.task_id, "depends_on_task_id": d.depends_on_task_id, "dep_type": d.dep_type}
                          for d in db.query(TaskDependency).filter(TaskDependency.task_id.in_([t.id for t in tasks])).all()],
    }


# ══════════════════════════════════════════════════════════════
# 项目仪表盘概览
# ══════════════════════════════════════════════════════════════

@router.get("/dashboard/overview")
def project_dashboard_overview(pid: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """项目仪表盘概览"""
    if pid:
        return _project_detail_dashboard(pid, db)
    total = db.query(Project).filter(Project.is_deleted == False).count()
    by_class = db.query(Project.project_class, sa_func.count(Project.id)).filter(Project.is_deleted == False).group_by(Project.project_class).all()
    by_status = db.query(Project.status, sa_func.count(Project.id)).filter(Project.is_deleted == False).group_by(Project.status).all()
    by_source = db.query(Project.source, sa_func.count(Project.id)).filter(Project.is_deleted == False).group_by(Project.source).all()
    today = date.today()
    overdue = db.query(Project).filter(Project.is_deleted == False, Project.target_end_date.isnot(None),
                                       Project.target_end_date < today, Project.status.in_(["planning", "running"])).count()
    high_risk = db.query(Risk).filter(Risk.risk_level == "A", Risk.status.in_(["open", "monitoring"])).count()
    total_gates = db.query(ProjectGate).count()
    passed_gates = db.query(ProjectGate).filter(ProjectGate.status == "passed").count()
    return {"total_projects": total, "by_class": {r[0]: r[1] for r in by_class},
            "by_status": {r[0]: r[1] for r in by_status}, "by_source": {r[0]: r[1] for r in by_source},
            "overdue_count": overdue, "high_risk_count": high_risk,
            "gate_progress": {"total": total_gates, "passed": passed_gates,
                              "rate": round(passed_gates / total_gates * 100, 1) if total_gates > 0 else 0}}


def _project_detail_dashboard(pid: int, db: Session) -> dict:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    gates = db.query(ProjectGate).filter(ProjectGate.project_id == pid).order_by(ProjectGate.seq).all()
    gate_progress = {"total": len(gates), "passed": sum(1 for g in gates if g.status == "passed"),
                     "items": [{"code": g.gate_code, "name": g.gate_name, "status": g.status, "seq": g.seq} for g in gates]}
    tasks = db.query(Task).filter(Task.project_id == pid).all()
    task_stats = {"total": len(tasks), "todo": sum(1 for t in tasks if t.status == "todo"),
                  "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
                  "done": sum(1 for t in tasks if t.status == "done"),
                  "blocked": sum(1 for t in tasks if t.status == "blocked")}
    milestones = db.query(Milestone).filter(Milestone.project_id == pid).order_by(Milestone.planned_date).all()
    milestone_stats = {"total": len(milestones), "achieved": sum(1 for m in milestones if m.status == "achieved"),
                        "delayed": sum(1 for m in milestones if m.status == "delayed")}
    risks = db.query(Risk).filter(Risk.project_id == pid).all()
    risk_stats = {"total": len(risks), "open": sum(1 for r in risks if r.status == "open"),
                   "a_level": sum(1 for r in risks if r.risk_level == "A")}
    today = date.today()
    is_overdue = bool(p.target_end_date and p.target_end_date < today and p.status in ("planning", "running"))
    return {"gate_progress": gate_progress, "task_stats": task_stats,
            "milestone_stats": milestone_stats, "risk_stats": risk_stats,
            "is_overdue": is_overdue, "days_remaining": (p.target_end_date - today).days if p.target_end_date else None,
            "health": "overdue" if is_overdue else "at_risk" if risk_stats["a_level"] > 0 or task_stats["blocked"] > 0 else "on_track"}


# ═══════════════ 项目对比 ═══════════════

class CompareRequest(BaseModel):
    project_ids: list[int]


@router.post("/compare")
def compare_projects(data: CompareRequest, db: Session = Depends(get_db)):
    """多项目对比"""
    projects = db.query(Project).filter(Project.id.in_(data.project_ids)).all()
    if len(projects) < 2:
        raise HTTPException(400, "至少选择2个项目")
    if len(projects) > 4:
        raise HTTPException(400, "最多对比4个项目")
    result_projects = []
    for p in projects:
        tasks = db.query(Task).filter(Task.project_id == p.id).all()
        risks = db.query(Risk).filter(Risk.project_id == p.id).all()
        result_projects.append({"id": p.id, "code": p.code, "name": p.name,
                                "project_class": p.project_class, "status": p.status,
                                "source": p.source, "owner": p.owner,
                                "start_date": str(p.start_date) if p.start_date else None,
                                "target_end_date": str(p.target_end_date) if p.target_end_date else None,
                                "budget": p.budget,
                                "_taskStats": {"total": len(tasks), "todo": sum(1 for t in tasks if t.status == "todo"),
                                               "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
                                               "done": sum(1 for t in tasks if t.status == "done")},
                                "_riskStats": {"total": len(risks), "a_level": sum(1 for r in risks if r.risk_level == "A")}})
    all_gates = {}
    for p in projects:
        gates = db.query(ProjectGate).filter(ProjectGate.project_id == p.id).order_by(ProjectGate.seq).all()
        for g in gates:
            key = f"{g.gate_code}|{g.gate_name}"
            if key not in all_gates:
                all_gates[key] = {"gate_code": g.gate_code, "gate_name": g.gate_name, "per_project": []}
            all_gates[key]["per_project"].append({"project_id": p.id, "status": g.status})
    return {"projects": result_projects, "gates": list(all_gates.values())}


# ═══════════════ 跨模块联动 ═══════════════

@router.get("/{pid}/cross-module")
def project_cross_module(pid: int, db: Session = Depends(get_db)):
    """返回项目关联的跨模块数据"""
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    result: dict = {}
    if p.product_code:
        product = db.query(Product).filter(Product.code == p.product_code).first()
        if product:
            result["product"] = {"id": product.id, "code": product.code, "name": product.name,
                                 "status": product.status, "category": product.category}
            boms = db.query(BOM).filter(BOM.product_id == product.id).all()
            result["boms"] = [{"id": b.id, "name": b.name, "bom_type": b.bom_type, "status": b.status} for b in boms]
    try:
        from app.models.test import Certification
        certs = db.query(Certification).filter(Certification.project_id == pid).order_by(Certification.created_at.desc()).limit(10).all()
        result["certifications"] = [{"id": c.id, "name": c.cert_name, "type": c.cert_type, "status": c.status} for c in certs]
    except Exception:
        logger.exception("unexpected error")
        result["certifications"] = []
    try:
        from app.models.test import ECR
        ecrs = db.query(ECR).filter(ECR.project_id == pid).order_by(ECR.created_at.desc()).limit(10).all()
        result["ecrs"] = [{"id": e.id, "title": e.title, "status": e.status,
                           "created_at": str(e.created_at.date()) if e.created_at else None} for e in ecrs]
    except Exception:
        logger.exception("unexpected error")
        result["ecrs"] = []
    entries = db.query(TimeEntry).join(Task).filter(Task.project_id == pid).all()
    result["total_hours"] = sum(e.hours or 0 for e in entries)
    result["time_entries_count"] = len(entries)
    comments_count = db.query(TaskComment).join(Task).filter(Task.project_id == pid).count()
    result["comments_count"] = comments_count
    return result


# ═══════════════ 项目导出 ═══════════════

@router.get("/{pid}/export")
def project_export(pid: int, db: Session = Depends(get_db)):
    """导出项目完整数据(JSON)"""
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    tasks = db.query(Task).filter(Task.project_id == pid).all()
    milestones = db.query(Milestone).filter(Milestone.project_id == pid).all()
    gates = db.query(ProjectGate).filter(ProjectGate.project_id == pid).order_by(ProjectGate.seq).all()
    risks = db.query(Risk).filter(Risk.project_id == pid).all()
    return {"project": {"code": p.code, "name": p.name, "project_class": p.project_class,
                        "source": p.source, "status": p.status, "owner": p.owner,
                        "product_code": p.product_code, "budget": p.budget,
                        "start_date": str(p.start_date) if p.start_date else None,
                        "target_end_date": str(p.target_end_date) if p.target_end_date else None,
                        "actual_end_date": str(p.actual_end_date) if p.actual_end_date else None,
                        "description": p.description},
            "gates": [{"code": g.gate_code, "name": g.gate_name, "status": g.status,
                        "planned_date": str(g.planned_date) if g.planned_date else None,
                        "actual_date": str(g.actual_date) if g.actual_date else None} for g in gates],
            "milestones": [{"name": m.name, "status": m.status,
                            "planned_date": str(m.planned_date) if m.planned_date else None,
                            "actual_date": str(m.actual_date) if m.actual_date else None} for m in milestones],
            "tasks": [{"title": t.title, "assignee": t.assignee, "status": t.status, "priority": t.priority,
                        "planned_date": str(t.planned_date) if t.planned_date else None,
                        "due_date": str(t.due_date) if t.due_date else None} for t in tasks],
            "risks": [{"title": r.title, "risk_level": r.risk_level, "status": r.status,
                        "probability": r.probability, "impact": r.impact} for r in risks],
            "exported_at": str(datetime.now())}


# ═══════════════ 项目通知提醒 ═══════════════

@router.get("/{pid}/alerts")
def project_alerts(pid: int, db: Session = Depends(get_db)):
    """聚合项目相关提醒: 超期任务/风险预警/里程碑延期"""
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "项目不存在")
    today = date.today()
    alerts_list = []
    overdue_tasks = db.query(Task).filter(Task.project_id == pid, Task.due_date < today,
                                          Task.status.in_(["todo", "in_progress", "blocked"])).all()
    for t in overdue_tasks:
        days = (today - t.due_date).days if t.due_date else 0
        alerts_list.append({"type": "task_overdue", "severity": "high",
                            "title": f"任务超期: {t.title}", "detail": f"已超期 {days} 天，负责人: {t.assignee or '-'}",
                            "date": str(t.due_date) if t.due_date else None})
    near_due = db.query(Task).filter(Task.project_id == pid, Task.due_date >= today,
                                     Task.due_date <= today + timedelta(days=3),
                                     Task.status.in_(["todo", "in_progress"])).all()
    for t in near_due:
        days = (t.due_date - today).days if t.due_date else 0
        alerts_list.append({"type": "task_due_soon", "severity": "medium",
                            "title": f"任务即将到期: {t.title}", "detail": f"还剩 {days} 天，负责人: {t.assignee or '-'}",
                            "date": str(t.due_date)})
    open_risks = db.query(Risk).filter(Risk.project_id == pid, Risk.risk_level == "A",
                                       Risk.status.in_(["open", "monitoring"])).all()
    for r in open_risks:
        alerts_list.append({"type": "risk_alert", "severity": "critical", "title": f"A级风险: {r.title}",
                            "detail": f"来源: {r.risk_source or '-'}，概率: {r.probability}，影响: {r.impact}",
                            "date": str(r.created_at.date()) if r.created_at else None})
    delayed_ms = db.query(Milestone).filter(Milestone.project_id == pid, Milestone.status == "delayed").all()
    for m in delayed_ms:
        alerts_list.append({"type": "milestone_delayed", "severity": "high", "title": f"里程碑延期: {m.name}",
                            "detail": f"延期里程碑，关联Gate: {m.gate_code or '-'}",
                            "date": str(m.planned_date) if m.planned_date else None})
    return sorted(alerts_list, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))
