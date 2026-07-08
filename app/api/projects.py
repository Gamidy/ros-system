"""项目管理API — 项目(T/A/B/C) CRUD + Gate模板"""
from datetime import date, datetime, timedelta
import random
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.project import Program, Project, ProjectGate, Milestone, Task, Risk
from app.models.bom import BOM
from app.models.product import Product
from app.services.state_machine import assert_transition
from app.schemas import (
    ProgramCreate, ProgramOut, ProjectCreate, ProjectUpdate, ProjectOut,
)

logger = logging.getLogger(__name__)

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
    return name[0] + "*" + name[-1]


# ══════════════════════════════════════════════════════════════
# Gate Templates by Project Class
# ══════════════════════════════════════════════════════════════

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

GATE_TEMPLATE_B = [
    {"code": "M2", "name": "方案与计划评审", "seq": 2, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M3", "name": "详细设计评审",   "seq": 3, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M6", "name": "量产准备",       "seq": 7, "decision_level": "项目经理", "is_high_risk_zone": True,  "is_hidden": False},
    {"code": "M7", "name": "量产评审",       "seq": 8, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M8", "name": "市场发布",       "seq": 9, "decision_level": "总经理",  "is_high_risk_zone": False, "is_hidden": False},
]

GATE_TEMPLATE_C = [
    {"code": "M2", "name": "方案与计划评审", "seq": 2, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M3", "name": "详细设计评审",   "seq": 3, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
    {"code": "M6", "name": "量产准备",       "seq": 7, "decision_level": "项目经理", "is_high_risk_zone": False, "is_hidden": False},
]

GATE_TEMPLATES = {"T": GATE_TEMPLATE_TA, "A": GATE_TEMPLATE_TA, "B": GATE_TEMPLATE_B, "C": GATE_TEMPLATE_C}
GATE_SEQ = {g["code"]: g["seq"] for g in GATE_TEMPLATE_TA}

SOURCE_CATEGORY_MAP = {
    "P01": "product_creation", "P02": "product_creation", "P07": "product_creation",
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


def _validate_gate_transition(project_id: int, target_code: str, new_status: str, db: Session) -> None:
    """Gate状态流转校验: 前置Gate必须passed才允许当前Gate passed"""
    if new_status != "passed":
        return
    target_seq = GATE_SEQ.get(target_code)
    if target_seq is None:
        raise HTTPException(status_code=400, detail=f"无效Gate编号: {target_code}")
    existing_gates = db.query(ProjectGate).filter(ProjectGate.project_id == project_id).all()
    existing_codes = {g.gate_code: g.status for g in existing_gates}
    project = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    template = _get_gate_template(project.project_class)
    template_codes_ordered = [g["code"] for g in template]
    if target_code not in template_codes_ordered:
        raise HTTPException(status_code=400, detail=f"Gate {target_code} 不在当前项目等级模板中")
    idx = template_codes_ordered.index(target_code)
    for prev_code in template_codes_ordered[:idx]:
        prev_status = existing_codes.get(prev_code)
        if prev_status != "passed":
            raise HTTPException(status_code=400,
                detail=f"前置Gate {prev_code} 未通过 (当前状态: {prev_status or '不存在'})")


# ══════════════════════════════════════════════════════════════
# Program (项目群) Endpoints
# ══════════════════════════════════════════════════════════════

@program_router.get("", response_model=list[ProgramOut])
def list_programs(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_menu("projects")),
) -> list[ProgramOut]:
    q = db.query(Program)
    if status:
        q = q.filter(Program.status == status)
    return q.order_by(Program.created_at.desc()).all()


@program_router.post("")
def create_program(
    req: ProgramCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    if db.query(Program).filter(Program.code == req.code).first():
        raise HTTPException(status_code=400, detail="项目群编号已存在")
    p = Program(code=req.code, name=req.name, description=req.description,
                start_date=req.start_date, end_date=req.end_date)
    db.add(p); db.commit(); db.refresh(p)
    return p


@program_router.get("/{pid}")
def get_program(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> dict:
    p = db.query(Program).filter(Program.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目群不存在")
    return {
        "id": p.id, "code": p.code, "name": p.name, "description": p.description,
        "status": p.status, "start_date": p.start_date, "end_date": p.end_date,
        "created_at": p.created_at, "updated_at": p.updated_at,
        "projects": [{"id": prj.id, "code": prj.code, "name": prj.name,
                       "project_class": prj.project_class, "status": prj.status,
                       "owner": _mask_name(prj.owner),
                       "start_date": prj.start_date, "target_end_date": prj.target_end_date}
                      for prj in p.projects],
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
) -> dict:
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
        q = q.filter((Project.name.like(like_pattern)) | (Project.code.like(like_pattern)))
    total = q.count()
    items = q.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [{"id": p.id, "code": p.code, "name": p.name, "program_id": p.program_id,
                    "product_code": p.product_code, "project_class": p.project_class,
                    "source": p.source, "source_category": p.source_category,
                    "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
                    "status": p.status, "start_date": p.start_date,
                    "target_end_date": p.target_end_date, "actual_end_date": p.actual_end_date,
                    "critical_path": p.critical_path,
                    "owner": _mask_name(p.owner), "description": p.description,
                    "market_policy": p.market_policy, "annual_planning_ref": p.annual_planning_ref,
                    "budget": p.budget, "is_draft": p.is_draft,
                    "created_at": p.created_at, "updated_at": p.updated_at} for p in items],
        "total": total, "page": page, "page_size": page_size,
    }


@project_router.post("", response_model=ProjectOut)
def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin", "systems_engineer")),
) -> ProjectOut:
    from app.core.sanitize import sanitize_html
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    code = req.code
    if not code:
        code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
    if db.query(Project).filter(Project.code == code).first():
        raise HTTPException(status_code=400, detail="项目编号已存在")
    name_dup = db.query(Project).filter(
        Project.name == req.name.strip(), Project.is_deleted == False, Project.is_draft == False,
    ).first()
    if name_dup:
        raise HTTPException(status_code=400, detail=f"项目名称「{req.name.strip()}」已存在（ID: {name_dup.id}），请更换名称")
    project_class = req.project_class if req.project_class else 'C'
    if req.program_id and not db.query(Program).filter(Program.id == req.program_id).first():
        raise HTTPException(status_code=400, detail="项目群不存在")
    source_category = _auto_source_category(req.source)
    p = Project(
        code=code, name=sanitize_html(req.name.strip()),
        project_class=project_class, program_id=req.program_id,
        product_code=req.product_code, source=req.source,
        source_category=source_category,
        dev_modules=req.dev_modules, change_impacts=req.change_impacts,
        start_date=req.start_date, target_end_date=req.target_end_date,
        owner=sanitize_html(req.owner.strip()) if req.owner else None,
        description=sanitize_html(req.description) if req.description else None,
        critical_path=req.critical_path,
        market_policy=req.market_policy, annual_planning_ref=req.annual_planning_ref,
        budget=req.budget,
    )
    db.add(p)
    db.flush()
    try:
        template = _get_gate_template(project_class)
        for gate_def in template:
            db.add(ProjectGate(project_id=p.id, gate_code=gate_def["code"],
                    gate_name=gate_def["name"], seq=gate_def["seq"],
                    decision_level=gate_def["decision_level"],
                    is_high_risk_zone=gate_def["is_high_risk_zone"],
                    is_hidden=gate_def["is_hidden"]))
        db.commit()
        db.refresh(p)
        if req.target_market:
            try:
                from app.services.cert_auto_gen import CertAutoGenService
                CertAutoGenService(db).generate_from_project(p.id)
            except Exception:
                logger.debug(f"ignored: {{e}}")
                pass
    except Exception as e:
        logger.exception(f"unexpected: {e}")
        db.rollback()
        logger.error(f"项目创建失败: {e}")
        raise
    return {"id": p.id, "code": p.code, "name": p.name, "program_id": p.program_id,
            "product_code": p.product_code, "project_class": p.project_class,
            "source": p.source, "source_category": p.source_category,
            "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
            "status": p.status, "start_date": p.start_date,
            "target_end_date": p.target_end_date, "actual_end_date": p.actual_end_date,
            "critical_path": p.critical_path, "owner": p.owner, "description": p.description,
            "market_policy": p.market_policy, "annual_planning_ref": p.annual_planning_ref,
            "budget": p.budget, "created_at": p.created_at, "updated_at": p.updated_at}


@project_router.get("/{pid}", response_model=ProjectOut)
def get_project_detail(pid: int, db: Session = Depends(get_db), _=Depends(require_menu("projects"))) -> ProjectOut:
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "id": p.id, "code": p.code, "name": p.name, "program_id": p.program_id,
        "product_code": p.product_code, "project_class": p.project_class,
        "source": p.source, "source_category": p.source_category,
        "dev_modules": p.dev_modules, "change_impacts": p.change_impacts,
        "status": p.status, "start_date": p.start_date,
        "target_end_date": p.target_end_date, "actual_end_date": p.actual_end_date,
        "critical_path": p.critical_path, "owner": p.owner, "description": p.description,
        "created_at": p.created_at, "updated_at": p.updated_at,
        "gates": [{"id": g.id, "gate_code": g.gate_code, "gate_name": g.gate_name, "seq": g.seq,
                    "decision_level": g.decision_level, "decider": g.decider, "status": g.status,
                    "planned_date": g.planned_date, "actual_date": g.actual_date,
                    "pass_conditions": g.pass_conditions, "decision": g.decision,
                    "reviewer": g.reviewer, "is_high_risk_zone": g.is_high_risk_zone,
                    "is_hidden": g.is_hidden, "project_id": g.project_id, "created_at": g.created_at}
                  for g in sorted(p.gates, key=lambda x: x.seq)],
        "milestones": [{"id": m.id, "name": m.name, "planned_date": m.planned_date,
                        "actual_date": m.actual_date, "status": m.status,
                        "conditions": m.conditions, "gate_code": m.gate_code}
                       for m in p.milestones],
        "risks": [{"id": r.id, "title": r.title, "risk_level": r.risk_level,
                    "risk_source": r.risk_source, "probability": r.probability,
                    "impact": r.impact, "mitigation": r.mitigation, "status": r.status,
                    "raised_by": r.raised_by, "resolved_at": r.resolved_at,
                    "created_at": r.created_at, "project_id": r.project_id}
                  for r in p.risks],
    }


@project_router.patch("/{pid}")
def update_project(
    pid: int, body: ProjectUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "product_manager", "project_admin")),
) -> dict:
    from app.core.sanitize import sanitize_html
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    updated = False
    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="项目名称不能为空")
        p.name = sanitize_html(body.name.strip()); updated = True
    if body.status is not None:
        if body.status not in ("planning", "running", "completed", "paused", "cancelled"):
            raise HTTPException(status_code=400, detail=f"无效状态: {body.status}")
        try:
            assert_transition("Project", p.status, body.status)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        p.status = body.status
        if body.status == "completed":
            p.actual_end_date = body.actual_end_date or date.today()
        updated = True
    if body.owner is not None:
        p.owner = sanitize_html(body.owner.strip()); updated = True
    if body.target_end_date is not None:
        p.target_end_date = body.target_end_date; updated = True
    if body.actual_end_date is not None:
        p.actual_end_date = body.actual_end_date; updated = True
    if body.description is not None:
        p.description = sanitize_html(body.description); updated = True
    if body.customer_name is not None:
        p.customer_name = sanitize_html(body.customer_name.strip()); updated = True
    if body.other_requirements is not None:
        p.other_requirements = sanitize_html(body.other_requirements); updated = True
    if body.budget is not None:
        p.budget = body.budget; updated = True
    if not updated:
        raise HTTPException(status_code=400, detail="未提供任何更新字段")
    db.commit(); db.refresh(p)
    return {"message": "更新成功", "id": p.id, "status": p.status, "owner": p.owner}


@project_router.delete("/{pid}")
def delete_project(
    pid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "project_admin")),
) -> dict:
    """软删除项目"""
    p = db.query(Project).filter(Project.id == pid, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在或已被删除")
    p.is_deleted = True
    db.commit()
    return {"message": "项目已删除", "id": pid, "name": p.name}


router = project_router  # alias for import compatibility
