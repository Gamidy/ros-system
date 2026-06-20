"""项目管理API: Program群 → Project(T/A/B/C) → M1~M9 Gate → Task + 里程碑 + 风险"""
from datetime import date, datetime
import random
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.project import Program, Project, ProjectGate, Milestone, Task, Risk
from app.schemas import (
    ProgramCreate, ProjectCreate, ProjectUpdate, ProjectOut, TaskCreate, RiskCreate,
    MilestoneCreate, GateStatusUpdate,
)

program_router = APIRouter(prefix="/programs", tags=["项目群管理"])
project_router = APIRouter(prefix="/projects", tags=["项目管理"])


# ══════════════════════════════════════════════════════════════
# Owner 姓名脱敏
# ══════════════════════════════════════════════════════════════

def _mask_name(name: str | None) -> str | None:
    """姓名脱敏: 张三→张*, 李四光→李*光"""
    if not name or not name.strip():
        return name
    name = name.strip()
    if len(name) == 1:
        return "*"
    if len(name) == 2:
        return name[0] + "*"
    # len >= 3: 保留首尾，中间用 * 替代
    return name[0] + "*" + name[-1]


# ══════════════════════════════════════════════════════════════
# Gate Templates by Project Class
# ══════════════════════════════════════════════════════════════

# T/A级: M1~M9 完整流程 + M5A隐藏节点
GATE_TEMPLATE_TA = [
    {"code": "M1",  "name": "需求与概念评审", "seq": 1,  "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M2",  "name": "方案与计划评审", "seq": 2,  "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M3",  "name": "详细设计评审",   "seq": 3,  "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M4",  "name": "样机与验证",     "seq": 4,  "decision_level": "项目经理", "is_high_risk_zone": True,  "is_hidden": False},
    {"code": "M5",  "name": "小批试产",       "seq": 5,  "decision_level": "项目经理", "is_high_risk_zone": True,  "is_hidden": False},
    {"code": "M5A", "name": "客户确认",       "seq": 6,  "decision_level": "项目经理", "is_high_risk_zone": True,  "is_hidden": True},
    {"code": "M6",  "name": "量产准备",       "seq": 7,  "decision_level": "项目经理", "is_high_risk_zone": True,  "is_hidden": False},
    {"code": "M7",  "name": "量产评审",       "seq": 8,  "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M8",  "name": "市场发布",       "seq": 9,  "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M9",  "name": "项目结项",       "seq": 10, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
]

# B级: M2/M3/M6/M7/M8 (无M1总经理拍板, 无M4/M5/M5A/M9)
GATE_TEMPLATE_B = [
    {"code": "M2", "name": "方案与计划评审", "seq": 2, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M3", "name": "详细设计评审",   "seq": 3, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M6", "name": "量产准备",       "seq": 7, "decision_level": "项目经理", "is_high_risk_zone": True,  "is_hidden": False},
    {"code": "M7", "name": "量产评审",       "seq": 8, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M8", "name": "市场发布",       "seq": 9, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
]

# C级: M2/M3/M6 简化 (项目经理决策, 无高风险区)
GATE_TEMPLATE_C = [
    {"code": "M2", "name": "方案与计划评审", "seq": 2, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M3", "name": "详细设计评审",   "seq": 3, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M6", "name": "量产准备",       "seq": 7, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
]

GATE_TEMPLATES = {
    "T": GATE_TEMPLATE_TA,
    "A": GATE_TEMPLATE_TA,
    "B": GATE_TEMPLATE_B,
    "C": GATE_TEMPLATE_C,
}

# Gate code → seq mapping for transition validation
GATE_SEQ = {g["code"]: g["seq"] for g in GATE_TEMPLATE_TA}

# Source auto-categorization
SOURCE_CATEGORY_MAP = {
    "P01": "product_creation",  "P02": "product_creation",  "P07": "product_creation",
    "P03": "product_optimization", "P04": "product_optimization",
    "P05": "product_optimization", "P06": "product_optimization",
}


def _get_gate_template(project_class: str) -> list[dict]:
    template = GATE_TEMPLATES.get(project_class)
    if not template:
        raise HTTPException(status_code=400, detail=f"无效项目等级: {project_class}")
    return template


def _auto_source_category(source: str | None) -> str | None:
    """根据来源编码自动归类"""
    if not source:
        return None
    return SOURCE_CATEGORY_MAP.get(source, None)


def _validate_gate_transition(project_id: int, target_code: str, new_status: str, db: Session):
    """Gate状态流转校验: 前置Gate必须passed才允许当前Gate passed"""
    if new_status != "passed":
        return  # 只校验passed操作

    target_seq = GATE_SEQ.get(target_code)
    if target_seq is None:
        raise HTTPException(status_code=400, detail=f"无效Gate编号: {target_code}")

    # 获取已存的所有Gate
    existing_gates = db.query(ProjectGate).filter(
        ProjectGate.project_id == project_id
    ).all()
    existing_codes = {g.gate_code: g.status for g in existing_gates}

    # 获取当前项目等级对应的模板codes
    project = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    template = _get_gate_template(project.project_class)
    template_codes_ordered = [g["code"] for g in template]

    # 找到target在模板中的位置
    if target_code not in template_codes_ordered:
        raise HTTPException(status_code=400, detail=f"Gate {target_code} 不在当前项目等级模板中")

    idx = template_codes_ordered.index(target_code)

    # 所有排在target之前的gate都必须是passed
    for prev_code in template_codes_ordered[:idx]:
        prev_status = existing_codes.get(prev_code)
        if prev_status != "passed":
            raise HTTPException(
                status_code=400,
                detail=f"前置Gate {prev_code} 未通过 (当前状态: {prev_status or '不存在'})"
            )


# ══════════════════════════════════════════════════════════════
# Program (项目群) Endpoints
# ══════════════════════════════════════════════════════════════

@program_router.get("")
def list_programs(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
):
    q = db.query(Program)
    if status:
        q = q.filter(Program.status == status)
    return q.order_by(Program.created_at.desc()).all()


@program_router.post("")
def create_program(
    req: ProgramCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    if db.query(Program).filter(Program.code == req.code).first():
        raise HTTPException(status_code=400, detail="项目群编号已存在")
    p = Program(code=req.code, name=req.name, description=req.description,
                start_date=req.start_date, end_date=req.end_date)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@program_router.get("/{pid}")
def get_program(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    p = db.query(Program).filter(Program.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目群不存在")
    return {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "projects": [
            {
                "id": prj.id,
                "code": prj.code,
                "name": prj.name,
                "project_class": prj.project_class,
                "status": prj.status,
                "owner": _mask_name(prj.owner),
                "start_date": prj.start_date,
                "target_end_date": prj.target_end_date,
            }
            for prj in p.projects
        ],
    }


# ══════════════════════════════════════════════════════════════
# Project Endpoints
# ══════════════════════════════════════════════════════════════

@project_router.get("")
def list_projects(
    program_id: int | None = Query(None),
    project_class: str | None = Query(None, pattern="^(T|A|B|C)$"),
    status: str | None = Query(None),
    product_code: str | None = Query(None),
    source: str | None = Query(None),
    source_category: str | None = Query(None),
    keyword: str | None = Query(None, description="按项目名称/编号模糊搜索"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数，最大100"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
):
    q = db.query(Project).filter(Project.is_deleted == False)
    if program_id is not None:
        q = q.filter(Project.program_id == program_id)
    if project_class:
        q = q.filter(Project.project_class == project_class)
    if status:
        q = q.filter(Project.status == status)
    if product_code:
        q = q.filter(Project.product_code == product_code)
    if source:
        q = q.filter(Project.source == source)
    if source_category:
        q = q.filter(Project.source_category == source_category)
    if keyword:
        like_pattern = f"%{keyword}%"
        q = q.filter(
            (Project.name.like(like_pattern)) | (Project.code.like(like_pattern))
        )

    total = q.count()
    items = q.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Build response with pagination metadata
    result = {
        "items": [{
            "id": p.id, "code": p.code, "name": p.name,
            "program_id": p.program_id, "product_code": p.product_code,
            "project_class": p.project_class, "source": p.source,
            "source_category": p.source_category,
            "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
            "status": p.status, "start_date": p.start_date,
            "target_end_date": p.target_end_date,
            "actual_end_date": p.actual_end_date,
            "critical_path": p.critical_path,
            "owner": _mask_name(p.owner), "description": p.description,
            "market_policy": p.market_policy, "annual_planning_ref": p.annual_planning_ref, "budget": p.budget,
            "is_draft": p.is_draft,
            "created_at": p.created_at, "updated_at": p.updated_at,
        } for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return result


@project_router.post("", response_model=ProjectOut)
def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    from app.core.sanitize import sanitize_html

    # 手动校验项目名称
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    # 自动生成项目编号（如果未填写）
    code = req.code
    if not code:
        code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"

    if db.query(Project).filter(Project.code == code).first():
        raise HTTPException(status_code=400, detail="项目编号已存在")

    # 同名检查：排除草稿（草稿允许重名，正式项目不允许重名）
    name_dup = db.query(Project).filter(
        Project.name == req.name.strip(),
        Project.is_deleted == False,
        Project.is_draft == False,
    ).first()
    if name_dup:
        raise HTTPException(status_code=400, detail=f"项目名称「{req.name.strip()}」已存在（ID: {name_dup.id}），请更换名称")

    # 默认项目等级
    project_class = req.project_class if req.project_class else 'C'

    # 验证program存在
    if req.program_id and not db.query(Program).filter(Program.id == req.program_id).first():
        raise HTTPException(status_code=400, detail="项目群不存在")

    # 自动分类来源
    source_category = _auto_source_category(req.source)

    p = Project(
        code=code,
        name=sanitize_html(req.name.strip()),
        project_class=project_class,
        program_id=req.program_id, product_code=req.product_code,
        source=req.source, source_category=source_category,
        dev_modules=req.dev_modules, change_impacts=req.change_impacts,
        start_date=req.start_date, target_end_date=req.target_end_date,
        owner=sanitize_html(req.owner.strip()) if req.owner else None,
        description=sanitize_html(req.description) if req.description else None,
        critical_path=req.critical_path,
        market_policy=req.market_policy, annual_planning_ref=req.annual_planning_ref, budget=req.budget,
    )
    db.add(p)
    db.flush()

    try:
        # 根据项目等级自动生成Gate模板
        template = _get_gate_template(project_class)
        for gate_def in template:
            db.add(ProjectGate(
                project_id=p.id,
                gate_code=gate_def["code"],
                gate_name=gate_def["name"],
                seq=gate_def["seq"],
                decision_level=gate_def["decision_level"],
                is_high_risk_zone=gate_def["is_high_risk_zone"],
                is_hidden=gate_def["is_hidden"],
            ))

        db.commit()
        db.refresh(p)
    except Exception:
        db.rollback()
        raise
    return {
        "id": p.id, "code": p.code, "name": p.name,
        "program_id": p.program_id, "product_code": p.product_code,
        "project_class": p.project_class, "source": p.source,
        "source_category": p.source_category,
        "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
        "status": p.status, "start_date": p.start_date,
        "target_end_date": p.target_end_date,
        "actual_end_date": p.actual_end_date,
        "critical_path": p.critical_path,
        "owner": p.owner, "description": p.description,
        "market_policy": p.market_policy, "annual_planning_ref": p.annual_planning_ref, "budget": p.budget,
        "created_at": p.created_at, "updated_at": p.updated_at,
    }


@project_router.get("/{pid}", response_model=ProjectOut)
def get_project_detail(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "id": p.id, "code": p.code, "name": p.name,
        "program_id": p.program_id, "product_code": p.product_code,
        "project_class": p.project_class, "source": p.source,
        "source_category": p.source_category,
        "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
        "status": p.status, "start_date": p.start_date,
        "target_end_date": p.target_end_date,
        "actual_end_date": p.actual_end_date,
        "critical_path": p.critical_path,
        "owner": p.owner, "description": p.description,
        "created_at": p.created_at, "updated_at": p.updated_at,
        "gates": [
            {
                "id": g.id, "gate_code": g.gate_code, "gate_name": g.gate_name,
                "seq": g.seq, "decision_level": g.decision_level,
                "decider": g.decider, "status": g.status,
                "planned_date": g.planned_date, "actual_date": g.actual_date,
                "pass_conditions": g.pass_conditions, "decision": g.decision,
                "reviewer": g.reviewer,
                "is_high_risk_zone": g.is_high_risk_zone,
                "is_hidden": g.is_hidden,
                "project_id": g.project_id,
                "created_at": g.created_at,
            }
            for g in sorted(p.gates, key=lambda x: x.seq)
        ],
        "milestones": [
            {
                "id": m.id, "name": m.name,
                "planned_date": m.planned_date, "actual_date": m.actual_date,
                "status": m.status, "conditions": m.conditions,
                "gate_code": m.gate_code,
            }
            for m in p.milestones
        ],
        "risks": [
            {
                "id": r.id, "title": r.title, "risk_level": r.risk_level,
                "risk_source": r.risk_source, "probability": r.probability,
                "impact": r.impact, "mitigation": r.mitigation,
                "status": r.status, "raised_by": r.raised_by,
                "resolved_at": r.resolved_at, "created_at": r.created_at,
                "project_id": r.project_id,
            }
            for r in p.risks
        ],
    }


@project_router.patch("/{pid}")
def update_project(
    pid: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    from app.core.sanitize import sanitize_html

    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    updated = False

    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="项目名称不能为空")
        p.name = sanitize_html(body.name.strip())
        updated = True

    if body.status is not None:
        if body.status not in ("planning", "running", "completed", "paused", "cancelled"):
            raise HTTPException(status_code=400, detail=f"无效状态: {body.status}")
        p.status = body.status
        if body.status == "completed":
            p.actual_end_date = body.actual_end_date or date.today()
        updated = True

    if body.owner is not None:
        p.owner = sanitize_html(body.owner.strip())
        updated = True

    if body.target_end_date is not None:
        p.target_end_date = body.target_end_date
        updated = True

    if body.actual_end_date is not None:
        p.actual_end_date = body.actual_end_date
        updated = True

    if body.description is not None:
        p.description = sanitize_html(body.description)
        updated = True

    if body.customer_name is not None:
        p.customer_name = sanitize_html(body.customer_name.strip())
        updated = True

    if body.other_requirements is not None:
        p.other_requirements = sanitize_html(body.other_requirements)
        updated = True

    if body.budget is not None:
        p.budget = body.budget
        updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="未提供任何更新字段")

    db.commit()
    db.refresh(p)
    return {"message": "更新成功", "id": p.id, "status": p.status, "owner": p.owner}


@project_router.delete("/{pid}")
def delete_project(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "project_admin")),
):
    """软删除项目：设置 is_deleted=True，不物理删除数据"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在或已被删除")
    p.is_deleted = True
    db.commit()
    return {"message": "项目已删除", "id": pid, "name": p.name}


# ══════════════════════════════════════════════════════════════
# Gate Management
# ══════════════════════════════════════════════════════════════

@project_router.get("/{pid}/gates")
def list_gates(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    gates = db.query(ProjectGate).filter(
        ProjectGate.project_id == pid
    ).order_by(ProjectGate.seq).all()
    return gates


@project_router.post("/{pid}/gates")
def create_gate(
    pid: int,
    gate_code: str,
    gate_name: str,
    seq: int,
    decision_level: str | None = None,
    pass_conditions: str | None = None,
    planned_date: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if db.query(ProjectGate).filter(
        ProjectGate.project_id == pid,
        ProjectGate.gate_code == gate_code,
    ).first():
        raise HTTPException(status_code=400, detail=f"Gate {gate_code} 已存在")
    g = ProjectGate(
        project_id=pid, gate_code=gate_code, gate_name=gate_name,
        seq=seq, decision_level=decision_level,
        pass_conditions=pass_conditions, planned_date=planned_date,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@project_router.post("/{pid}/gates/bulk")
def bulk_create_gates(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    """根据项目等级自动生成全部M1~M9 Gate，或覆盖不全的"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    template = _get_gate_template(p.project_class)
    existing = {
        g.gate_code: g
        for g in db.query(ProjectGate).filter(ProjectGate.project_id == pid).all()
    }

    created, skipped = [], []
    for gate_def in template:
        code = gate_def["code"]
        if code in existing:
            skipped.append(code)
            continue
        g = ProjectGate(
            project_id=pid,
            gate_code=code,
            gate_name=gate_def["name"],
            seq=gate_def["seq"],
            decision_level=gate_def["decision_level"],
            is_high_risk_zone=gate_def["is_high_risk_zone"],
            is_hidden=gate_def["is_hidden"],
        )
        db.add(g)
        created.append(code)

    db.commit()
    return {"created": created, "skipped": skipped, "total": len(created)}


@project_router.patch("/{pid}/gates/{gate_code}")
def update_gate_status(
    pid: int,
    gate_code: str,
    status: str,
    actual_date: date | None = None,
    decision: str | None = None,
    reviewer: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    gate = db.query(ProjectGate).filter(
        ProjectGate.project_id == pid,
        ProjectGate.gate_code == gate_code,
    ).first()
    if not gate:
        raise HTTPException(status_code=404, detail=f"Gate {gate_code} 不存在")

    # Gate流转校验: passed需要前置Gate已通过
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

    db.commit()
    db.refresh(gate)
    return gate


# ══════════════════════════════════════════════════════════════
# Task Management
# ══════════════════════════════════════════════════════════════

@project_router.get("/{pid}/tasks")
def list_tasks(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return db.query(Task).filter(Task.project_id == pid).order_by(Task.created_at.desc()).all()


@project_router.post("/{pid}/tasks")
def create_task(
    pid: int,
    req: TaskCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if req.milestone_id and not db.query(Milestone).filter(
        Milestone.id == req.milestone_id, Milestone.project_id == pid
    ).first():
        raise HTTPException(status_code=400, detail="里程碑不存在或不属于该项目")
    if req.priority not in ("low", "medium", "high", "urgent"):
        raise HTTPException(status_code=400, detail="无效优先级")

    t = Task(
        project_id=pid, title=req.title, assignee=req.assignee,
        milestone_id=req.milestone_id, priority=req.priority,
        planned_date=req.planned_date, due_date=req.due_date,
        description=req.description,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@project_router.patch("/{pid}/tasks/{tid}")
def update_task(
    pid: int,
    tid: int,
    status: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    due_date: date | None = None,
    description: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    t = db.query(Task).filter(Task.id == tid, Task.project_id == pid).first()
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    if status:
        if status not in ("todo", "in_progress", "done", "blocked"):
            raise HTTPException(status_code=400, detail="无效状态")
        t.status = status
        if status == "done":
            t.actual_date = date.today()
    if assignee is not None:
        t.assignee = assignee
    if priority:
        if priority not in ("low", "medium", "high", "urgent"):
            raise HTTPException(status_code=400, detail="无效优先级")
        t.priority = priority
    if due_date is not None:
        t.due_date = due_date
    if description is not None:
        t.description = description
    db.commit()
    db.refresh(t)
    return t


# ══════════════════════════════════════════════════════════════
# Milestone Management
# ══════════════════════════════════════════════════════════════

@project_router.get("/{pid}/milestones")
def list_milestones(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return db.query(Milestone).filter(Milestone.project_id == pid).order_by(Milestone.created_at.desc()).all()


@project_router.post("/{pid}/milestones")
def create_milestone(
    pid: int,
    req: MilestoneCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    m = Milestone(
        project_id=pid, name=req.name, planned_date=req.planned_date,
        conditions=req.conditions, gate_code=req.gate_code,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@project_router.patch("/{pid}/milestones/{mid}")
def achieve_milestone(
    pid: int,
    mid: int,
    status: str = "achieved",
    actual_date: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    m = db.query(Milestone).filter(
        Milestone.id == mid, Milestone.project_id == pid
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    if status == "achieved":
        m.status = "achieved"
        m.actual_date = actual_date or date.today()

        # Auto-complete关联任务
        linked_tasks = db.query(Task).filter(Task.milestone_id == mid).all()
        for t in linked_tasks:
            if t.status != "done":
                t.status = "done"
                t.actual_date = date.today()
    else:
        m.status = status

    db.commit()
    db.refresh(m)
    return {
        "milestone": m,
        "auto_completed_tasks": len(
            db.query(Task).filter(Task.milestone_id == mid).all()
        ),
    }


# ══════════════════════════════════════════════════════════════
# Delay Chain Warning (延期传导链预警)
# ══════════════════════════════════════════════════════════════

@project_router.get("/{pid}/delay-chain")
def get_delay_chain(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    """延期传导链预警: 计算里程碑依赖链的延期放大效应
    
    示例输出:
    [
      {
        "milestone": "设计评审",
        "delay_days": 5,
        "impacts": [
          {"downstream_milestone": "样机制作", "amplification": 1.6, "estimated_impact_days": 8},
          {"downstream_milestone": "实验验证", "amplification": 3.0, "estimated_impact_days": 15},
          ...
        ]
      }
    ]
    """
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")

    milestones = db.query(Milestone).filter(Milestone.project_id == pid).all()
    if not milestones:
        return {"project_id": pid, "project_name": p.name, "chains": [], "overall_amplification": None}

    # Build dependency map
    milestone_map: dict[int, Milestone] = {m.id: m for m in milestones}
    
    # Compute delay for each milestone that has actual_date
    delays: dict[int, int] = {}  # milestone_id → delay_days
    for m in milestones:
        if m.actual_date and m.planned_date:
            d = (m.actual_date - m.planned_date).days
            if d > 0:
                delays[m.id] = d

    # Build downstream index: which milestones depend on each
    downstream_map: dict[int, list[int]] = {}  # upstream_id → [downstream_ids]
    for m in milestones:
        if m.depends_on_milestone_id and m.depends_on_milestone_id in milestone_map:
            upstream_id = m.depends_on_milestone_id
            if upstream_id not in downstream_map:
                downstream_map[upstream_id] = []
            downstream_map[upstream_id].append(m.id)

    # Default amplification factor per dependency level
    DEFAULT_AMPLIFICATION = 1.5

    def walk_chain(upstream_id: int, accumulated_amplification: float, visited: set) -> list[dict]:
        """Recursively walk downstream to compute impact chains"""
        impacts = []
        if upstream_id not in downstream_map:
            return impacts
        
        for down_id in downstream_map[upstream_id]:
            if down_id in visited:
                continue
            down_m = milestone_map[down_id]
            
            # Compute amplification for this edge
            # If both upstream and downstream have actual delay data, use real ratio
            if upstream_id in delays and down_id in delays:
                edge_amp = delays[down_id] / max(delays[upstream_id], 1)
            else:
                edge_amp = DEFAULT_AMPLIFICATION
            
            total_amp = round(accumulated_amplification * edge_amp, 2)
            estimated_impact = round(delays.get(upstream_id, 0) * total_amp)
            
            new_visited = visited | {down_id}
            
            impact_entry = {
                "downstream_milestone": down_m.name,
                "downstream_milestone_id": down_m.id,
                "amplification": total_amp,
                "estimated_impact_days": estimated_impact,
                "downstream_delay_days": delays.get(down_id, None),  # actual delay if known
                "downstream_status": down_m.status,
            }
            
            # Recursively walk further downstream
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
                chains.append({
                    "milestone": m.name,
                    "milestone_id": m.id,
                    "delay_days": delays[m.id],
                    "planned_date": str(m.planned_date) if m.planned_date else None,
                    "actual_date": str(m.actual_date) if m.actual_date else None,
                    "impacts": impact_list,
                })

    # Compute overall amplification: max downstream estimated impact / root delay
    overall_amplification = None
    if chains:
        all_impacts = []
        for chain in chains:
            for imp in chain["impacts"]:
                all_impacts.append(imp["amplification"])
        if all_impacts:
            overall_amplification = round(max(all_impacts), 2)

    return {
        "project_id": pid,
        "project_name": p.name,
        "project_class": p.project_class,
        "total_milestones": len(milestones),
        "delayed_milestones": len(delays),
        "chains": chains,
        "overall_amplification": overall_amplification,
    }


# ══════════════════════════════════════════════════════════════
# Risk Management
# ══════════════════════════════════════════════════════════════

@project_router.get("/{pid}/risks")
def list_risks(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return db.query(Risk).filter(Risk.project_id == pid).order_by(Risk.created_at.desc()).all()


@project_router.post("/{pid}/risks")
def create_risk(
    pid: int,
    req: RiskCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if req.risk_level not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="风险等级须为A/B/C")
    if req.probability not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="无效概率")
    if req.impact not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="无效影响度")

    r = Risk(
        project_id=pid, title=req.title, risk_level=req.risk_level,
        risk_source=req.risk_source, probability=req.probability,
        impact=req.impact, mitigation=req.mitigation,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@project_router.patch("/{pid}/risks/{rid}")
def update_risk(
    pid: int,
    rid: int,
    status: str | None = None,
    mitigation: str | None = None,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
):
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
    db.commit()
    db.refresh(r)
    return r
