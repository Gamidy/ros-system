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
from app.models.proposal_approval import ProposalApproval, ProposalParallelReviewer
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest
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
# 辅助: 校验审批人配置（提交前预检，也便于系统设置页面复用）
# ══════════════════════════════════════════════════════════════════

def _validate_approver_config(db: Session) -> list[str]:
    """校验每个并行审批角色和研发总监必须恰好有1个在职用户

    Returns:
        list[str] — 问题描述列表，空列表表示校验通过
    """
    errors: list[str] = []

    # 校验4个并行审批角色
    for role in _PARALLEL_ROLES:
        users = db.query(User).filter(User.role == role, User.is_active == True).all()
        label = _ROLE_LABEL.get(role, role)
        count = len(users)
        if count == 0:
            errors.append(f"无法提交：以下角色未配置审批人：{label}（{count}人）")
        elif count > 1:
            errors.append(f"无法提交：以下角色配置了多个审批人：{label}（{count}人）")

    # 校验研发总监
    director = db.query(User).filter(User.role == "rd_director", User.is_active == True).all()
    d_label = _ROLE_LABEL.get("rd_director", "研发总监")
    d_count = len(director)
    if d_count == 0:
        errors.append(f"无法提交：以下角色未配置审批人：{d_label}（{d_count}人）")
    elif d_count > 1:
        errors.append(f"无法提交：以下角色配置了多个审批人：{d_label}（{d_count}人）")

    return errors


# ══════════════════════════════════════════════════════════════════
# 辅助: 状态变更 + 同步通用审批表（绑定在一起，杜绝遗漏）
# ══════════════════════════════════════════════════════════════════

def _change_status(db: Session, pa: ProposalApproval, new_status: str):
    """变更 ProposalApproval 状态并同步 ApprovalRequest

    禁止在业务代码中直接写 pa.status = "..."，必须通过本函数。
    """
    pa.status = new_status
    _sync_approval_request(db, pa)


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
        "series_name": p.series_name,
        "energy_rating": p.energy_rating,
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
        "cert_costs": p.cert_costs,
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
    # 从独立表加载并行审批人数据（旧 JSON 列仅做兼容读取）
    parallel_reviewers = _load_parallel_reviewers(pa)
    return {
        "id": pa.id,
        "proposal_id": pa.proposal_id,
        "proposer_id": pa.proposer_id,
        "title": pa.title,
        "status": pa.status,
        "parallel_reviewers": parallel_reviewers,
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


def _load_parallel_reviewers(pa: ProposalApproval) -> list[dict]:
    """从独立表或旧 JSON 列加载并行审批人列表"""
    from app.core.database import SessionLocal
    # 优先从新表读取
    db = SessionLocal()
    try:
        rows = (
            db.query(ProposalParallelReviewer)
            .filter(ProposalParallelReviewer.approval_id == pa.id)
            .order_by(ProposalParallelReviewer.id)
            .all()
        )
        if rows:
            result = []
            for r in rows:
                result.append({
                    "user_id": r.user_id,
                    "username": r.username or "",
                    "role": r.role or "",
                    "status": r.status,
                    "reason": r.reason or "",
                    "reviewed_at": str(r.reviewed_at) if r.reviewed_at else None,
                })
            return result
    finally:
        db.close()

    # fallback: 旧 JSON 列（兼容旧数据）
    return pa.parallel_reviewers or []


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
# 辅助: 确保立项审批链存在
# ══════════════════════════════════════════════════════════════════

def _ensure_proposal_chain(db: Session) -> ApprovalChain:
    """确保 'proposal' 审批链存在，不存在则创建"""
    chain = db.query(ApprovalChain).filter(ApprovalChain.code == "proposal").first()
    if not chain:
        chain = ApprovalChain(
            name="立项审批",
            code="proposal",
            description="产品立项审批流程（并行审批 + 研发总监终审）",
        )
        db.add(chain)
        db.flush()
        steps_def = [
            {"seq": 1, "role": "产品经理", "name": "产品经理提交"},
            {"seq": 2, "role": "并行审批人", "name": "模块经理/工程师并行审批"},
            {"seq": 3, "role": "研发总监", "name": "研发总监终审"},
        ]
        for s in steps_def:
            db.add(ApprovalStep(chain_id=chain.id, seq=s["seq"], role=s["role"], name=s["name"]))
        db.flush()
    return chain


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

    # ── 2b. 校验审批人配置：每个并行角色+总监必须恰好1人 ──
    config_errors = _validate_approver_config(db)
    if config_errors:
        raise HTTPException(status_code=400, detail="；".join(config_errors))

    # ── 3. 查找并行审批人 (4个角色) ──
    parallel_reviewers = []
    for role in _PARALLEL_ROLES:
        user = db.query(User).filter(User.role == role, User.is_active == True).first()
        if user:
            parallel_reviewers.append({
                "user_id": user.id,
                "username": user.username,
                "role": _ROLE_LABEL.get(role, role),
                "status": "pending",
                "reason": "",
                "reviewed_at": None,
            })

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
        parallel_reviewers=None,  # 不再写入 JSON 列
        director_reviewer_id=director_id,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
        resubmit_count=resubmit_count,
    )
    db.add(pa)
    db.flush()

    # ── 6a. 插入并行审批人独立表 ──
    for reviewer in parallel_reviewers:
        pr = ProposalParallelReviewer(
            approval_id=pa.id,
            user_id=reviewer["user_id"],
            username=reviewer["username"],
            role=reviewer["role"],
            status="pending",
            reason="",
            reviewed_at=None,
        )
        db.add(pr)
    db.flush()
    p.is_draft = False
    p.status = 'submitted'

    # ── 6a. 创建对应的 ApprovalRequest（供通用审批列表显示） ──
    proposal_chain = _ensure_proposal_chain(db)
    approval_req = ApprovalRequest(
        chain_id=proposal_chain.id,
        request_type="proposal",
        request_id=pa.id,  # 关联 ProposalApproval 的 ID
        title=p.name or "",
        requester=current_user.username,
        status="pending",  # 映射: pending_parallel → pending
        current_step=1,
    )
    db.add(approval_req)
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

    from app.core.permissions import is_super_role
    is_admin = is_super_role(current_user.role)

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
        if is_admin:
            results.append(_proposal_to_out(pa))
            continue
        # 从独立表查询并行审批人
        reviewer_rows = db.query(ProposalParallelReviewer).filter(
            ProposalParallelReviewer.approval_id == pa.id,
            ProposalParallelReviewer.user_id == user_id,
            ProposalParallelReviewer.status == "pending",
        ).all()
        if reviewer_rows:
            results.append(_proposal_to_out(pa))
            continue
        # fallback: 旧 JSON 列兼容
        reviewers = pa.parallel_reviewers or []
        for r in reviewers:
            if r.get("user_id") == user_id and r.get("status") == "pending":
                results.append(_proposal_to_out(pa))
                break

    # ── 研发总监: pending_director 状态 ──
    if not status or status == "pending_director":
        director_query = db.query(ProposalApproval).filter(
            ProposalApproval.status == "pending_director",
        )
        if not is_admin:
            director_query = director_query.filter(
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


def _sync_approval_request(db: Session, pa: ProposalApproval):
    """同步 ApprovalRequest 状态（供通用审批列表查询）"""
    ar = db.query(ApprovalRequest).filter(
        ApprovalRequest.request_type == "proposal",
        ApprovalRequest.request_id == pa.id,
    ).first()
    if not ar:
        return
    # 映射 ProposalApproval 状态到 ApprovalRequest 状态
    status_map = {
        "pending_parallel": "pending",
        "pending_director": "pending",
        "approved": "approved",
        "rejected": "rejected",
        "withdrawn": "withdrawn",
    }
    new_status = status_map.get(pa.status, "pending")
    if ar.status != new_status:
        ar.status = new_status

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
    from app.core.permissions import is_super_role
    is_admin = is_super_role(current_user.role)
    is_director = (pa.director_reviewer_id == user_id) and not is_admin
    is_parallel = False
    reviewer_index = -1

    if not is_admin:
        # 从独立表查询并行审批人身份
        reviewer_row = db.query(ProposalParallelReviewer).filter(
            ProposalParallelReviewer.approval_id == pa.id,
            ProposalParallelReviewer.user_id == user_id,
        ).first()
        if reviewer_row:
            is_parallel = True
            reviewer_index = -1  # not needed for atomic update
        elif pa.parallel_reviewers:
            # fallback: 旧 JSON 列兼容
            for i, r in enumerate(pa.parallel_reviewers):
                if r.get("user_id") == user_id:
                    is_parallel = True
                    reviewer_index = i
                    break

    if not is_admin and not is_parallel and not is_director:
        raise HTTPException(status_code=403, detail="您不是该审批的审批人")

    # ═══════════════════════ 管理员操作（可审批任意阶段）═══════════════════════
    if is_admin:
        if pa.status not in ("pending_parallel", "pending_director"):
            raise HTTPException(status_code=400, detail="当前不在审批阶段")

        if action == "rejected":
            _change_status(db, pa, "rejected")
            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批被管理员驳回: {pa.title}",
                content=f"管理员 {current_user.username} 驳回了项目「{pa.title}」的立项申请。"
                        + (f"原因: {reason}" if reason else ""),
            )
        else:  # approved
            _change_status(db, pa, "approved")

            project = db.query(Project).filter(Project.id == pa.proposal_id, Project.is_deleted == False).first()
            if project and project.status != 'planning':
                import random
                if not project.code:
                    code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
                    while db.query(Project).filter(Project.code == code, Project.is_deleted == False).first():
                        code = f"PRJ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
                    project.code = code
                project.is_draft = False
                project.status = "planning"

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

            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批已通过: {pa.title}",
                content=f"您的项目「{pa.title}」已通过管理员审批，现已正式立项。",
            )

        db.commit()
        db.refresh(pa)
        return {
            "message": "审批操作成功",
            "approval": _proposal_to_out(pa),
        }

    # ═══════════════════════ 并行审批人操作 ═══════════════════════
    if is_parallel:
        if pa.status != "pending_parallel":
            raise HTTPException(status_code=400, detail="当前不在并行审批阶段")

        # 原子更新：仅当该行 status='pending' 时才更新（防止并发覆盖）
        from sqlalchemy import update as sa_update
        stmt = (
            sa_update(ProposalParallelReviewer)
            .where(
                ProposalParallelReviewer.approval_id == pa.id,
                ProposalParallelReviewer.user_id == user_id,
                ProposalParallelReviewer.status == "pending",
            )
            .values(
                status=action,
                reason=reason or "",
                reviewed_at=now,
            )
        )
        result = db.execute(stmt)
        if result.rowcount == 0:
            # 检查是否已审批过（而不是 pending 被并发抢走导致 rowcount=0）
            existing = db.query(ProposalParallelReviewer).filter(
                ProposalParallelReviewer.approval_id == pa.id,
                ProposalParallelReviewer.user_id == user_id,
            ).first()
            if existing and existing.status != "pending":
                raise HTTPException(status_code=400, detail="您已审批过该申请")
            else:
                raise HTTPException(status_code=400, detail="审批状态异常，请重试")
        db.flush()

        if action == "rejected":
            # 驳回 → 整个审批结束
            _change_status(db, pa, "rejected")

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
                r.status == "approved" for r in
                db.query(ProposalParallelReviewer)
                .filter(ProposalParallelReviewer.approval_id == pa.id)
                .all()
            )
            if all_approved:
                # 全部通过 → 进入研发总监审批
                _change_status(db, pa, "pending_director")

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
            _change_status(db, pa, "rejected")

            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批被研发总监驳回: {pa.title}",
                content=f"研发总监驳回了项目「{pa.title}」的立项申请。"
                        + (f"原因: {reason}" if reason else ""),
            )
        else:
            # 通过 → 自动创建项目 (草稿 → 正式)
            # 注意：状态赋值在所有副作用代码之后，commit() 之前
            project = db.query(Project).filter(Project.id == pa.proposal_id, Project.is_deleted == False).first()
            if project and project.status != 'planning':
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

            # 状态赋值放在所有副作用代码之后，commit() 之前最后一步
            _change_status(db, pa, "approved")

        db.commit()
        db.refresh(pa)

        return {
            "message": "审批操作成功",
            "approval": _proposal_to_out(pa),
        }


# ══════════════════════════════════════════════════════════════════
# POST /api/pm/proposals/draft — 创建产品立项草稿
# ══════════════════════════════════════════════════════════════════

@router.post("/pm/proposals/draft")
def create_proposal_draft(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """产品经理保存立项草稿。接收完整表单数据，创建 Project(is_draft=True)。"""
    import random

    name = payload.get("name") or f"草稿-{current_user.username}-{datetime.now().strftime('%m%d%H%M')}"
    code = payload.get("code") or f"DRF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"

    p = Project(
        code=code,
        name=name,
        project_class=payload.get("project_class") or "C",
        program_id=payload.get("program_id"),
        product_code=payload.get("product_code"),
        source=payload.get("project_origin") or payload.get("source"),
        status="draft",
        start_date=_parse_date(payload.get("start_date")),
        target_end_date=_parse_date(payload.get("target_end_date")),
        owner=current_user.username,
        leader_id=payload.get("leader_id"),
        description=payload.get("background_basis"),
        market_policy=payload.get("market_policy"),
        annual_planning_ref=payload.get("annual_planning_ref"),
        budget=payload.get("budget"),
        product_type=payload.get("product_type"),
        target_market=payload.get("target_market"),
        climate_zone=payload.get("climate_zone"),
        refrigerant=payload.get("refrigerant"),
        capacity_range=payload.get("capacity_range"),
        voltage_freq=payload.get("voltage_freq"),
        series_name=payload.get("series_name"),
        energy_rating=payload.get("energy_rating"),
        ip_ownership=payload.get("ip_ownership"),
        project_duration=payload.get("project_duration"),
        dev_category=payload.get("dev_category"),
        project_origin=payload.get("project_origin"),
        background_basis=payload.get("background_basis"),
        overall_goal=payload.get("overall_goal"),
        tech_goal=payload.get("tech_goal"),
        cost_goal=payload.get("cost_goal"),
        sales_goal=payload.get("sales_goal"),
        cert_goal=payload.get("cert_goal"),
        schedule_goal=payload.get("schedule_goal"),
        patent_goal=payload.get("patent_goal"),
        other_goals=payload.get("other_goals"),
        is_draft=True,
    )
    db.add(p)
    db.flush()
    db.commit()
    return {"id": p.id, "code": p.code, "name": p.name}


# ══════════════════════════════════════════════════════════════════
# PUT /api/pm/proposals/draft — 更新产品立项草稿
# ══════════════════════════════════════════════════════════════════

@router.put("/pm/proposals/draft")
def update_proposal_draft(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新已有草稿。payload 必须包含 id 字段。"""
    draft_id = payload.get("id")
    if not draft_id:
        raise HTTPException(status_code=400, detail="缺少草稿 id")

    p = db.query(Project).filter(
        Project.id == draft_id,
        Project.is_draft == True,
        Project.owner == current_user.username,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="草稿不存在或无权修改")

    _apply_payload(p, payload)
    p.updated_at = datetime.now()
    db.commit()
    return {"id": p.id, "code": p.code, "name": p.name}


# ══════════════════════════════════════════════════════════════════
# GET /api/pm/proposals/draft — 获取当前用户的草稿列表
# ══════════════════════════════════════════════════════════════════

@router.get("/pm/proposals/draft")
def get_proposal_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前产品经理的立项草稿列表。查询 projects 表中 status='draft' 且 owner=当前用户的项目。"""
    drafts = (
        db.query(Project)
        .filter(
            Project.owner == current_user.username,
            Project.status == "draft",
            Project.is_deleted == False,
        )
        .order_by(Project.updated_at.desc())
        .all()
    )
    return [_project_to_snapshot(p) for p in drafts]


def _parse_date(val):
    """安全解析日期字符串"""
    if not val:
        return None
    try:
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(str(val)[:10], fmt).date()
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _apply_payload(p: Project, payload: dict):
    """将 payload 字典中的已知字段应用到 Project 对象"""
    mappings = [
        ("name", "name"), ("code", "code"), ("project_class", "project_class"),
        ("program_id", "program_id"), ("product_code", "product_code"),
        ("project_origin", "source"), ("source", "source"),
        ("status", "status"),
        ("leader_id", "leader_id"), ("budget", "budget"),
        ("product_type", "product_type"), ("target_market", "target_market"),
        ("climate_zone", "climate_zone"), ("refrigerant", "refrigerant"),
        ("capacity_range", "capacity_range"), ("voltage_freq", "voltage_freq"),
        ("series_name", "series_name"), ("energy_rating", "energy_rating"),
        ("ip_ownership", "ip_ownership"), ("project_duration", "project_duration"),
        ("dev_category", "dev_category"), ("project_origin", "project_origin"),
        ("background_basis", "background_basis"), ("overall_goal", "overall_goal"),
        ("tech_goal", "tech_goal"), ("cost_goal", "cost_goal"),
        ("sales_goal", "sales_goal"), ("cert_goal", "cert_goal"),
        ("schedule_goal", "schedule_goal"), ("patent_goal", "patent_goal"),
        ("other_goals", "other_goals"),
        ("market_policy", "market_policy"),
        ("annual_planning_ref", "annual_planning_ref"),
        ("description", "description"),
    ]
    for src_key, col_name in mappings:
        if src_key in payload and payload[src_key] is not None:
            setattr(p, col_name, payload[src_key])
    # Date fields
    for key in ["start_date", "target_end_date"]:
        if key in payload:
            setattr(p, key, _parse_date(payload[key]))


# ══════════════════════════════════════════════════════════════════
# POST /api/pm/proposals/{project_id}/withdraw — 撤销提交
# ══════════════════════════════════════════════════════════════════

@router.post("/pm/proposals/{project_id}/withdraw")
def withdraw_proposal(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """产品经理撤销已提交的立项审批

    前提条件:
    - 项目属于当前用户
    - 项目已提交（非草稿）
    - ProposalApproval 状态为 pending_parallel 或 pending_director

    效果:
    - 项目恢复为草稿状态 (is_draft=True, status='draft')
    - ProposalApproval 标记为 withdrawn
    - ApprovalRequest 标记为 withdrawn
    - 通知并行审批人和研发总监
    """
    # ── 1. 校验项目 ──
    p = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    if p.owner != current_user.username:
        raise HTTPException(status_code=403, detail="仅项目负责人可撤销立项申请")

    # ── 2. 查找进行中的审批 ──
    pa = (
        db.query(ProposalApproval)
        .filter(
            ProposalApproval.proposal_id == project_id,
            ProposalApproval.status.in_(["pending_parallel", "pending_director"]),
        )
        .first()
    )
    if not pa:
        raise HTTPException(status_code=400, detail="该项目没有进行中的审批，无法撤销")

    # ── 3. 恢复项目为草稿 ──
    p.is_draft = True
    p.status = "draft"

    # ── 4. 标记审批为撤销 ──
    _change_status(db, pa, "withdrawn")

    # ── 5. 同步 ApprovalRequest ──
    ar = db.query(ApprovalRequest).filter(
        ApprovalRequest.request_type == "proposal",
        ApprovalRequest.request_id == pa.id,
    ).first()
    if ar:
        ar.status = "withdrawn"

    # ── 6. 通知并行审批人（从独立表或旧JSON列查询） ──
    reviewer_rows = db.query(ProposalParallelReviewer).filter(
        ProposalParallelReviewer.approval_id == pa.id,
    ).all()
    if reviewer_rows:
        for r in reviewer_rows:
            _create_notification(
                db,
                target_user_id=r.user_id,
                title=f"立项审批已撤销: {pa.title}",
                content=f"产品经理 {current_user.username} 撤销了项目「{pa.title}」的立项申请。",
            )
    else:
        # fallback: 旧 JSON 列
        reviewers = pa.parallel_reviewers or []
        for reviewer in reviewers:
            if reviewer.get("user_id"):
                _create_notification(
                    db,
                    target_user_id=reviewer["user_id"],
                    title=f"立项审批已撤销: {pa.title}",
                    content=f"产品经理 {current_user.username} 撤销了项目「{pa.title}」的立项申请。",
                )

    # ── 7. 通知研发总监 ──
    if pa.director_reviewer_id:
        _create_notification(
            db,
            target_user_id=pa.director_reviewer_id,
            title=f"立项审批已撤销: {pa.title}",
            content=f"产品经理 {current_user.username} 撤销了项目「{pa.title}」的立项申请。",
        )

    db.commit()
    db.refresh(pa)

    return {
        "message": "已撤销提交，项目恢复为草稿状态",
        "project_id": p.id,
        "project_status": p.status,
        "approval_status": pa.status,
    }
