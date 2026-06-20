"""项目立项审批API

端点:
  POST /api/pm/proposals/submit  — 产品经理提交立项审批
  GET  /api/approvals/pending     — 当前用户待审批列表
  GET  /api/approvals/{id}        — 审批详情（含原始立项数据快照）
  POST /api/approvals/{id}/review — 审批操作（通过/驳回）

审批流程:
  1. 产品经理提交草稿项目 → 创建 ProposalApproval，状态=pending_parallel
  2. 并行审批（4位模块/工程师）→ 全部通过后状态=pending_director，任一驳回则 rejected
  3. 研发总监终审 → 通过后自动创建项目(草稿→正式)，驳回则 rejected
"""
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectGate
from app.models.proposal_approval import ProposalApproval
from app.models.alert import Notification

router = APIRouter(tags=["项目立项审批"])

# ── 角色 → 中文名称映射 ─────────────────────────────────────────────
_ROLE_LABEL = {
    "module_manager_struct": "结构模块经理",
    "module_manager_sys": "系统模块经理",
    "electrical_control_engineer": "电控工程师",
    "electrical_engineer": "电气工程师",
    "rd_director": "研发总监",
}

# 并行审批需要的4个角色
_PARALLEL_ROLES = [
    "module_manager_struct",
    "module_manager_sys",
    "electrical_control_engineer",
    "electrical_engineer",
]


# ══════════════════════════════════════════════════════════════════
# 辅助: 构建项目快照 (复制 pm_workspace._project_to_dict)
# ══════════════════════════════════════════════════════════════════

def _project_to_snapshot(p: Project) -> dict:
    """将 Project ORM 对象转为完整快照 dict"""
    return {
        "id": p.id,
        "code": p.code,
        "name": p.name,
        "project_class": p.project_class,
        "source": p.source,
        "source_category": p.source_category,
        "product_code": p.product_code,
        "status": p.status,
        "start_date": str(p.start_date) if p.start_date else None,
        "target_end_date": str(p.target_end_date) if p.target_end_date else None,
        "actual_end_date": str(p.actual_end_date) if p.actual_end_date else None,
        "owner": p.owner,
        "description": p.description,
        "critical_path": p.critical_path,
        "market_policy": p.market_policy,
        "annual_planning_ref": p.annual_planning_ref,
        "budget": p.budget,
        "program_id": p.program_id,
        "leader_id": p.leader_id,
        "dev_modules": p.dev_modules,
        "change_impacts": p.change_impacts,
        # Sheet 1
        "product_type": p.product_type,
        "target_market": p.target_market,
        "climate_zone": p.climate_zone,
        "refrigerant": p.refrigerant,
        "capacity_range": p.capacity_range,
        "voltage_freq": p.voltage_freq,
        "ip_ownership": p.ip_ownership,
        "project_duration": p.project_duration,
        "dev_category": p.dev_category,
        "project_origin": p.project_origin,
        "background_basis": p.background_basis,
        "overall_goal": p.overall_goal,
        "tech_goal": p.tech_goal,
        "cost_goal": p.cost_goal,
        "sales_goal": p.sales_goal,
        "cert_goal": p.cert_goal,
        "schedule_goal": p.schedule_goal,
        "patent_goal": p.patent_goal,
        "other_goals": p.other_goals,
        "deliverables": p.deliverables,
        "sample_qty": p.sample_qty,
        "required_date": str(p.required_date) if p.required_date else None,
        # Sheet 2
        "main_capacity": p.main_capacity,
        "energy_efficiency_req": p.energy_efficiency_req,
        "cert_requirements": p.cert_requirements,
        "target_price": p.target_price,
        "customer_requirements": p.customer_requirements,
        # Sheet 3
        "core_performance": p.core_performance,
        "safety_compliance": p.safety_compliance,
        "optional_config": p.optional_config,
        # Sheet 4
        "dev_cost_items": p.dev_cost_items,
        "economic_indicators": p.economic_indicators,
        "mold_costs": p.mold_costs,
        "prototype_costs_detail": p.prototype_costs_detail,
        "test_costs": p.test_costs,
        "labor_costs": p.labor_costs,
        # Sheet 5
        "team_members": p.team_members,
        # New fields
        "customer_name": p.customer_name,
        "other_requirements": p.other_requirements,
        "accessory_config": p.accessory_config,
        "feature_config": p.feature_config,
        "fob_price": p.fob_price,
        "bom_cost_target": p.bom_cost_target,
        "bom_cost_ratio": p.bom_cost_ratio,
        "manufacturing_cost": p.manufacturing_cost,
        "gross_margin": p.gross_margin,
        "annual_sales_forecast": p.annual_sales_forecast,
        "product_lifecycle": p.product_lifecycle,
        "mold_inner": p.mold_inner,
        "mold_outer": p.mold_outer,
        # Draft
        "is_draft": p.is_draft,
        "created_at": str(p.created_at) if p.created_at else None,
        "updated_at": str(p.updated_at) if p.updated_at else None,
    }


def _proposal_to_out(pa: ProposalApproval) -> dict:
    """将 ProposalApproval ORM 对象转为输出 dict"""
    return {
        "id": pa.id,
        "proposal_id": pa.proposal_id,
        "proposer_id": pa.proposer_id,
        "title": pa.title,
        "status": pa.status,
        "parallel_reviewers": pa.parallel_reviewers,
        "director_reviewer_id": pa.director_reviewer_id,
        "director_status": pa.director_status,
        "director_reason": pa.director_reason,
        "director_reviewed_at": str(pa.director_reviewed_at) if pa.director_reviewed_at else None,
        "snapshot": pa.snapshot,
        "previous_snapshot": pa.previous_snapshot,
        "resubmit_count": pa.resubmit_count,
        "reminded": pa.reminded,
        "escalated": pa.escalated,
        "created_at": str(pa.created_at) if pa.created_at else None,
        "updated_at": str(pa.updated_at) if pa.updated_at else None,
    }


# ══════════════════════════════════════════════════════════════════
# 辅助: 通知
# ══════════════════════════════════════════════════════════════════

def _create_notification(
    db: Session,
    target_user_id: int,
    title: str,
    content: str,
    channel: str = "system",
):
    """创建系统通知记录"""
    notif = Notification(
        target_user=str(target_user_id),
        channel=channel,
        title=title,
        content=content,
    )
    db.add(notif)
    db.flush()


# ══════════════════════════════════════════════════════════════════
# POST /api/pm/proposals/submit — 提交立项审批
# ══════════════════════════════════════════════════════════════════

@router.post("/pm/proposals/submit")
def submit_proposal(
    project_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """产品经理提交立项审批

    1. 查找草稿项目 (is_draft=True, owner=current_user)
    2. 创建 ProposalApproval 记录 + 保存快照
    3. 查找并行审批人 (结构/系统模块经理 + 电控/电气工程师)
    4. 查找研发总监
    5. 通知4位并行审批人
    """
    # ── 1. 校验项目 ──
    p = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可提交立项审批")
    if not p.is_draft:
        raise HTTPException(status_code=400, detail="该项目已提交或非草稿状态，无法重复提交")

    # ── 2. 检查是否已有进行中的审批 ──
    existing = (
        db.query(ProposalApproval)
        .filter(
            ProposalApproval.proposal_id == project_id,
            ProposalApproval.status.in_(["pending_parallel", "pending_director"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该项目已有进行中的审批")

    # ── 2a. 查找上一次被驳回的记录 (用于修改对比) ──
    previous_rejected = (
        db.query(ProposalApproval)
        .filter(
            ProposalApproval.proposal_id == project_id,
            ProposalApproval.status == "rejected",
        )
        .order_by(ProposalApproval.created_at.desc())
        .first()
    )
    previous_snapshot = None
    resubmit_count = 0
    if previous_rejected:
        previous_snapshot = previous_rejected.snapshot
        resubmit_count = (previous_rejected.resubmit_count or 0) + 1

    # ── 3. 查找并行审批人 (4个角色) ──
    parallel_reviewers = []
    for role in _PARALLEL_ROLES:
        users = db.query(User).filter(User.role == role, User.is_active == True).all()
        for u in users:
            parallel_reviewers.append({
                "user_id": u.id,
                "username": u.username,
                "role": _ROLE_LABEL.get(role, role),
                "status": "pending",
                "reason": "",
                "reviewed_at": None,
            })

    if not parallel_reviewers:
        # 如果系统中没有这些角色的用户，至少需要研发总监
        pass  # 继续执行，研发总监审批依然有效

    # ── 4. 查找研发总监 ──
    director = (
        db.query(User)
        .filter(User.role == "rd_director", User.is_active == True)
        .first()
    )
    director_id = director.id if director else None

    # ── 5. 保存快照 ──
    snapshot = _project_to_snapshot(p)

    # ── 6. 创建审批记录 ──
    pa = ProposalApproval(
        proposal_id=project_id,
        proposer_id=current_user.id,
        title=p.name or "",
        status="pending_parallel",
        parallel_reviewers=parallel_reviewers if parallel_reviewers else None,
        director_reviewer_id=director_id,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
        resubmit_count=resubmit_count,
    )
    db.add(pa)
    db.flush()

    # ── 7. 通知并行审批人 ──
    for reviewer in (parallel_reviewers or []):
        _create_notification(
            db,
            target_user_id=reviewer["user_id"],
            title=f"新项目立项审批: {p.name}",
            content=f"产品经理 {current_user.username} 提交了项目「{p.name}」的立项申请，请您进行并行审批。",
        )

    db.commit()
    db.refresh(pa)

    return {
        "message": "立项审批已提交",
        "approval": _proposal_to_out(pa),
    }


# ══════════════════════════════════════════════════════════════════
# GET /api/approvals/pending — 待审批列表
# ══════════════════════════════════════════════════════════════════

@router.get("/approvals/proposals")
def list_pending_approvals(
    mode: str = "pending",
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取审批列表
    mode=pending: 待当前用户审批
    mode=my: 当前用户提交的
    status: 按审批状态筛选 (pending_parallel/pending_director/approved/rejected)
    keyword: 按项目名称搜索
    """
    user_id = current_user.id

    if mode == "my":
        # 我提交的
        query = db.query(ProposalApproval).filter(ProposalApproval.proposer_id == user_id)
        if status:
            query = query.filter(ProposalApproval.status == status)
        if keyword:
            query = query.filter(ProposalApproval.title.ilike(f"%{keyword}%"))
        total = query.count()
        items = query.order_by(ProposalApproval.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"items": [_proposal_to_out(pa) for pa in items], "total": total}

    # mode=pending: 待我审批
    results = []

    # ── 并行审批: pending_parallel 状态 ──
    parallel_query = db.query(ProposalApproval).filter(
        ProposalApproval.status == "pending_parallel"
    )
    if keyword:
        parallel_query = parallel_query.filter(ProposalApproval.title.ilike(f"%{keyword}%"))
    if status and status != "pending_parallel":
        parallel_query = parallel_query.filter(False)  # skip if status filter excludes this
    parallel_pending = parallel_query.all()

    for pa in parallel_pending:
        reviewers = pa.parallel_reviewers or []
        for r in reviewers:
            if r.get("user_id") == user_id and r.get("status") == "pending":
                results.append(_proposal_to_out(pa))
                break

    # ── 研发总监: pending_director 状态 ──
    if not status or status == "pending_director":
        director_query = db.query(ProposalApproval).filter(
            ProposalApproval.status == "pending_director",
            ProposalApproval.director_reviewer_id == user_id,
        )
        if keyword:
            director_query = director_query.filter(ProposalApproval.title.ilike(f"%{keyword}%"))
        director_pending = director_query.all()
        for pa in director_pending:
            results.append(_proposal_to_out(pa))

    # ── 按状态筛选已完成的审批 (approved/rejected) ──
    if status and status in ("approved", "rejected"):
        completed_query = db.query(ProposalApproval).filter(
            ProposalApproval.status == status,
            ProposalApproval.proposer_id == user_id,
        )
        if keyword:
            completed_query = completed_query.filter(ProposalApproval.title.ilike(f"%{keyword}%"))
        completed = completed_query.order_by(ProposalApproval.created_at.desc()).all()
        for pa in completed:
            results.append(_proposal_to_out(pa))

    return {"items": results, "total": len(results)}


# ══════════════════════════════════════════════════════════════════
# GET /api/approvals/{id} — 审批详情
# ══════════════════════════════════════════════════════════════════

@router.get("/approvals/{approval_id}")
def get_approval_detail(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取审批详情（含原始立项数据快照 + 修改对比）"""
    pa = db.query(ProposalApproval).filter(ProposalApproval.id == approval_id).first()
    if not pa:
        raise HTTPException(status_code=404, detail="审批记录不存在")

    detail = _proposal_to_out(pa)

    # 附带 project 当前最新数据用于对比
    project = db.query(Project).filter(Project.id == pa.proposal_id, Project.is_deleted == False).first()
    if project:
        detail["project"] = _project_to_snapshot(project)

    return detail


# ══════════════════════════════════════════════════════════════════
# POST /api/approvals/{id}/review — 审批操作
# ══════════════════════════════════════════════════════════════════

@router.post("/approvals/{approval_id}/review")
def review_approval(
    approval_id: int,
    action: str = Body(..., pattern="^(approved|rejected)$"),
    reason: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批操作（通过/驳回）

    - 并行审批人: 更新 parallel_reviewers 中对应项
      - 驳回 → 整个审批状态改为 rejected，通知产品经理
      - 全部通过 → 状态改为 pending_director，通知研发总监
    - 研发总监:
      - 通过 → 状态改为 approved，自动创建项目 + 通知团队成员
      - 驳回 → 状态改为 rejected，通知产品经理
    """
    pa = db.query(ProposalApproval).filter(ProposalApproval.id == approval_id).first()
    if not pa:
        raise HTTPException(status_code=404, detail="审批记录不存在")

    user_id = current_user.id
    now = datetime.now()

    # ── 判断当前用户身份 ──
    is_director = pa.director_reviewer_id == user_id
    is_parallel = False
    reviewer_index = -1

    if pa.parallel_reviewers:
        for i, r in enumerate(pa.parallel_reviewers):
            if r.get("user_id") == user_id:
                is_parallel = True
                reviewer_index = i
                break

    if not is_parallel and not is_director:
        raise HTTPException(status_code=403, detail="您不是该审批的审批人")

    # ═══════════════════════ 并行审批人操作 ═══════════════════════
    if is_parallel:
        if pa.status != "pending_parallel":
            raise HTTPException(status_code=400, detail="当前不在并行审批阶段")

        if pa.parallel_reviewers[reviewer_index].get("status") != "pending":
            raise HTTPException(status_code=400, detail="您已审批过该申请")

        # 更新当前审批人状态
        pa.parallel_reviewers[reviewer_index]["status"] = action
        pa.parallel_reviewers[reviewer_index]["reason"] = reason or ""
        pa.parallel_reviewers[reviewer_index]["reviewed_at"] = str(now)

        if action == "rejected":
            # 驳回 → 整个审批结束
            pa.status = "rejected"

            # 通知产品经理
            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批被驳回: {pa.title}",
                content=f"审批人 {current_user.username} 驳回了项目「{pa.title}」的立项申请。"
                        + (f"原因: {reason}" if reason else ""),
            )
        else:
            # 检查是否全部通过
            all_approved = all(
                r.get("status") == "approved" for r in pa.parallel_reviewers
            )
            if all_approved:
                # 全部通过 → 进入研发总监审批
                pa.status = "pending_director"

                # 通知研发总监
                if pa.director_reviewer_id:
                    _create_notification(
                        db,
                        target_user_id=pa.director_reviewer_id,
                        title=f"立项审批待终审: {pa.title}",
                        content=f"项目「{pa.title}」的并行审批已全部通过，请您进行最终审批。",
                    )

        db.commit()
        db.refresh(pa)

        return {
            "message": "审批操作成功",
            "approval": _proposal_to_out(pa),
        }

    # ═══════════════════════ 研发总监操作 ═══════════════════════
    if is_director:
        if pa.status != "pending_director":
            raise HTTPException(status_code=400, detail="当前不在研发总监审批阶段")

        if pa.director_status != "pending":
            raise HTTPException(status_code=400, detail="您已审批过该申请")

        pa.director_status = action
        pa.director_reason = reason
        pa.director_reviewed_at = now

        if action == "rejected":
            # 驳回
            pa.status = "rejected"

            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批被研发总监驳回: {pa.title}",
                content=f"研发总监驳回了项目「{pa.title}」的立项申请。"
                        + (f"原因: {reason}" if reason else ""),
            )
        else:
            # 通过 → 自动创建项目 (草稿 → 正式)
            pa.status = "approved"

            project = db.query(Project).filter(Project.id == pa.proposal_id, Project.is_deleted == False).first()
            if project and project.is_draft:
                import random

                # 自动生成项目编号
                if not project.code:
                    code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
                    while db.query(Project).filter(Project.code == code, Project.is_deleted == False).first():
                        code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
                    project.code = code

                project.is_draft = False
                project.status = "planning"

                # 自动生成 Gate 模板
                existing_gates = (
                    db.query(ProjectGate)
                    .filter(ProjectGate.project_id == pa.proposal_id)
                    .count()
                )
                if existing_gates == 0:
                    from app.api.projects import _get_gate_template

                    project_class = project.project_class or "B"
                    template = _get_gate_template(project_class)
                    for gate_def in template:
                        db.add(
                            ProjectGate(
                                project_id=project.id,
                                gate_code=gate_def["code"],
                                gate_name=gate_def["name"],
                                seq=gate_def["seq"],
                                decision_level=gate_def["decision_level"],
                                is_high_risk_zone=gate_def["is_high_risk_zone"],
                                is_hidden=gate_def["is_hidden"],
                            )
                        )

                db.flush()

                # 通知团队成员 (从 team_members JSON 解析)
                team_members_str = project.team_members or "[]"
                try:
                    team_members = json.loads(team_members_str)
                except (json.JSONDecodeError, TypeError):
                    team_members = []

                for member in team_members:
                    if isinstance(member, dict) and member.get("user_id"):
                        _create_notification(
                            db,
                            target_user_id=member["user_id"],
                            title=f"项目已立项: {pa.title}",
                            content=f"项目「{pa.title}」已通过立项审批，现已正式进入研发阶段。",
                        )

            # 通知产品经理
            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批已通过: {pa.title}",
                content=f"您的项目「{pa.title}」已通过全部审批，现已正式立项。",
            )

        db.commit()
        db.refresh(pa)

        return {
            "message": "审批操作成功",
            "approval": _proposal_to_out(pa),
        }
