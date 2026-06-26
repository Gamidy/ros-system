"""研发总监面板 API

GET /api/rd/panel — 返回项目统计/进度/风险/审批中/延期数据
权限: rd_director 角色
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectGate, Risk
from app.models.approval import ApprovalRequest  # 统一审批引擎

router = APIRouter(prefix="/rd", tags=["研发总监面板"])


def _require_rd_director(current_user: User = Depends(get_current_user)) -> User:
    """仅研发总监可访问"""
    if current_user.role != "rd_director":
        raise HTTPException(status_code=403, detail="仅研发总监可访问")
    return current_user


@router.get("/panel")
def rd_panel(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_rd_director),
) -> dict:
    """研发总监面板 — 聚合项目统计/进度/风险/审批/延期"""
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # ── 1. 项目统计 ──
    total_projects = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False
    ).scalar() or 0

    active_projects = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
        Project.status.in_(["planning", "running"]),
    ).scalar() or 0

    completed_projects = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
        Project.status == "completed",
    ).scalar() or 0

    # 按等级分布
    class_distribution = {}
    for pc in ["T", "A", "B", "C"]:
        cnt = db.query(func.count(Project.id)).filter(
            Project.is_deleted == False,
            Project.project_class == pc,
        ).scalar() or 0
        class_distribution[pc] = cnt

    # ── 2. 进度概览 ──
    # 按状态统计
    status_distribution = {}
    for st in ["planning", "running", "completed", "paused", "cancelled"]:
        cnt = db.query(func.count(Project.id)).filter(
            Project.is_deleted == False,
            Project.status == st,
        ).scalar() or 0
        status_distribution[st] = cnt

    # Gate 进度: 已通过的 M1~M9 分布
    gate_progress = {}
    for gate_code in ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]:
        passed = db.query(func.count(ProjectGate.id)).join(
            Project, ProjectGate.project_id == Project.id
        ).filter(
            Project.is_deleted == False,
            ProjectGate.gate_code == gate_code,
            ProjectGate.status == "passed",
        ).scalar() or 0
        total_gates = db.query(func.count(ProjectGate.id)).join(
            Project, ProjectGate.project_id == Project.id
        ).filter(
            Project.is_deleted == False,
            ProjectGate.gate_code == gate_code,
        ).scalar() or 0
        gate_progress[gate_code] = {
            "passed": passed,
            "total": total_gates,
            "percent": round(passed / total_gates * 100, 1) if total_gates > 0 else 0,
        }

    # ── 3. 风险概览 ──
    total_risks = db.query(func.count(Risk.id)).join(
        Project, Risk.project_id == Project.id
    ).filter(
        Project.is_deleted == False,
        Risk.status != "resolved",
    ).scalar() or 0

    a_risks = db.query(func.count(Risk.id)).join(
        Project, Risk.project_id == Project.id
    ).filter(
        Project.is_deleted == False,
        Risk.risk_level == "A",
        Risk.status != "resolved",
    ).scalar() or 0

    b_risks = db.query(func.count(Risk.id)).join(
        Project, Risk.project_id == Project.id
    ).filter(
        Project.is_deleted == False,
        Risk.risk_level == "B",
        Risk.status != "resolved",
    ).scalar() or 0

    # M4-M6 高风险区项目 (Gate未通过)
    high_risk_zone = db.query(func.count(func.distinct(ProjectGate.project_id))).join(
        Project, ProjectGate.project_id == Project.id
    ).filter(
        Project.is_deleted == False,
        ProjectGate.gate_code.in_(["M4", "M5", "M6"]),
        ProjectGate.is_high_risk_zone == True,
        ProjectGate.status != "passed",
    ).scalar() or 0

    # ── 4. 审批中: 统一 ApprovalRequest 查询 ──
    pending_proposal_count = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == "pending",
        ApprovalRequest.request_type == "proposal",
    ).scalar() or 0

    # 近30天审批完成数
    recent_approved = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == "approved",
        ApprovalRequest.request_type == "proposal",
        ApprovalRequest.updated_at >= thirty_days_ago,
    ).scalar() or 0

    # ── 5. 延期项目 ──
    overdue_projects = db.query(Project).filter(
        Project.is_deleted == False,
        Project.target_end_date.isnot(None),
        Project.target_end_date < today,
        Project.status.in_(["planning", "running"]),
    ).order_by(Project.target_end_date.asc()).limit(10).all()

    overdue_list = []
    for p in overdue_projects:
        delay_days = (today - p.target_end_date).days if p.target_end_date else 0
        overdue_list.append({
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "project_class": p.project_class,
            "status": p.status,
            "owner": p.owner,
            "target_end_date": str(p.target_end_date) if p.target_end_date else None,
            "delay_days": delay_days,
        })

    overdue_count = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
        Project.target_end_date.isnot(None),
        Project.target_end_date < today,
        Project.status.in_(["planning", "running"]),
    ).scalar() or 0

    # ── 最近创建的项目 ──
    recent_projects = db.query(Project).filter(
        Project.is_deleted == False,
    ).order_by(Project.created_at.desc()).limit(5).all()

    recent_list = [{
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "project_class": p.project_class,
        "status": p.status,
        "owner": p.owner,
        "created_at": str(p.created_at) if p.created_at else None,
    } for p in recent_projects]

    return {
        # 项目统计
        "project_stats": {
            "total": total_projects,
            "active": active_projects,
            "completed": completed_projects,
            "class_distribution": class_distribution,
        },
        # 进度概览
        "progress": {
            "status_distribution": status_distribution,
            "gate_progress": gate_progress,
        },
        # 风险
        "risk": {
            "total_open_risks": total_risks,
            "a_level_risks": a_risks,
            "b_level_risks": b_risks,
            "m4_m6_high_risk_zone_projects": high_risk_zone,
        },
        # 审批
        "approvals": {
            "pending_proposal": pending_proposal_count,
            "recent_30d_approved": recent_approved,
        },
        # 延期
        "overdue": {
            "count": overdue_count,
            "top_10": overdue_list,
        },
        # 最近项目
        "recent_projects": recent_list,
    }
