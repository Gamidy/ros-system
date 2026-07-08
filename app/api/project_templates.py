"""项目模板API — 模板CRUD + 快速立项"""
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role, require_menu
from app.models.user import User
from app.models.project import Project, ProjectGate, Task, Milestone, ProjectTemplate

router = APIRouter(prefix="/project-templates", tags=["项目模板"])


@router.get("")
def list_templates(
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
):
    """列出所有激活的模板"""
    templates = db.query(ProjectTemplate).filter(ProjectTemplate.is_active == True).all()
    return [{
        "id": t.id, "name": t.name, "description": t.description,
        "project_class": t.project_class,
        "template_data": json.loads(t.template_data) if t.template_data else None,
        "created_at": str(t.created_at),
    } for t in templates]


@router.post("")
def create_template(
    name: str,
    project_class: str = "C",
    description: str | None = None,
    source_project_id: int | None = None,
    template_data: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager")),
) -> dict:
    """创建项目模板（可从已有项目提取）"""
    data = {}
    if source_project_id:
        # 从已有项目提取数据
        p = db.query(Project).filter(Project.id == source_project_id).first()
        if not p:
            raise HTTPException(404, "项目不存在")
        gates = db.query(ProjectGate).filter(ProjectGate.project_id == source_project_id).order_by(ProjectGate.seq).all()
        tasks = db.query(Task).filter(Task.project_id == source_project_id).all()
        milestones = db.query(Milestone).filter(Milestone.project_id == source_project_id).all()
        data = {
            "gates": [{"gate_code": g.gate_code, "gate_name": g.gate_name, "seq": g.seq,
                       "decision_level": g.decision_level, "is_high_risk_zone": g.is_high_risk_zone,
                       "is_hidden": g.is_hidden} for g in gates],
            "tasks": [{"title": t.title, "priority": t.priority, "description": t.description} for t in tasks],
            "milestones": [{"name": m.name, "conditions": m.conditions, "gate_code": m.gate_code} for m in milestones],
        }
        project_class = p.project_class
    elif template_data:
        data = json.loads(template_data)

    tpl = ProjectTemplate(
        name=name, description=description, project_class=project_class,
        template_data=json.dumps(data, ensure_ascii=False),
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return {"id": tpl.id, "ok": True}


@router.post("/{tid}/apply")
def apply_template(
    tid: int,
    project_name: str,
    project_code: str | None = None,
    owner: str | None = None,
    start_date: date | None = None,
    target_end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager")),
) -> dict:
    """应用模板创建新项目"""
    tpl = db.query(ProjectTemplate).filter(ProjectTemplate.id == tid, ProjectTemplate.is_active == True).first()
    if not tpl:
        raise HTTPException(404, "模板不存在")

    # 创建项目
    p = Project(
        code=project_code or f"TP-{date.today().strftime('%Y%m%d')}-{tid}",
        name=project_name,
        project_class=tpl.project_class,
        owner=owner,
        start_date=start_date or date.today(),
        target_end_date=target_end_date,
        status="planning",
    )
    db.add(p)
    db.flush()

    # 解析模板数据
    data = json.loads(tpl.template_data) if tpl.template_data else {}

    # 创建Gate
    for g in data.get("gates", []):
        gate = ProjectGate(
            project_id=p.id, gate_code=g["gate_code"], gate_name=g["gate_name"],
            seq=g.get("seq", 0), decision_level=g.get("decision_level"),
            is_high_risk_zone=g.get("is_high_risk_zone", False),
            is_hidden=g.get("is_hidden", False),
        )
        db.add(gate)

    # 创建任务
    for t in data.get("tasks", []):
        task = Task(project_id=p.id, title=t["title"], priority=t.get("priority", "medium"),
                     description=t.get("description"))
        db.add(task)

    # 创建里程碑
    for m in data.get("milestones", []):
        ms = Milestone(project_id=p.id, name=m["name"], conditions=m.get("conditions"),
                        gate_code=m.get("gate_code"))
        db.add(ms)

    db.commit()
    db.refresh(p)
    return {"id": p.id, "code": p.code, "name": p.name, "ok": True}


@router.delete("/{tid}")
def delete_template(
    tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager")),
) -> dict:
    """删除模板"""
    tpl = db.query(ProjectTemplate).filter(ProjectTemplate.id == tid).first()
    if not tpl:
        raise HTTPException(404, "模板不存在")
    tpl.is_active = False
    db.commit()
    return {"ok": True}
