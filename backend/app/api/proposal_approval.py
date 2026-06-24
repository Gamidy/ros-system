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
from app.models.proposal_approval import (
    ProposalApproval, ProposalParallelReviewer,
    ProposalStatus, ReviewStatus, ApprovalRequestStatus,
)
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest
from app.models.alert import Notification

from .proposal_utils import (
    _validate_approver_config, _change_status, _project_to_snapshot,
    _proposal_to_out, _load_parallel_reviewers, _create_notification,
    _ensure_proposal_chain, _sync_approval_request, _parse_date, _apply_payload,
    _ROLE_LABEL, _PARALLEL_ROLES,
)

router = APIRouter(tags=["项目立项审批"])


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
            ProposalApproval.status.in_([ProposalStatus.PENDING_PARALLEL, ProposalStatus.PENDING_DIRECTOR]),
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
            ProposalApproval.status == ProposalStatus.REJECTED,
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
                "status": ReviewStatus.PENDING,
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
        status=ProposalStatus.PENDING_PARALLEL,
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
            status=ReviewStatus.PENDING,
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
        status=ApprovalRequestStatus.PENDING,  # 映射: pending_parallel → pending
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
        ProposalApproval.status == ProposalStatus.PENDING_PARALLEL
    )
    if keyword:
        parallel_query = parallel_query.filter(ProposalApproval.title.ilike(f"%{keyword}%"))
    if status and status != ProposalStatus.PENDING_PARALLEL:
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
            ProposalParallelReviewer.status == ReviewStatus.PENDING,
        ).all()
        if reviewer_rows:
            results.append(_proposal_to_out(pa))
            continue
        # fallback: 旧 JSON 列兼容
        reviewers = pa.parallel_reviewers or []
        for r in reviewers:
            if r.get("user_id") == user_id and r.get("status") == ReviewStatus.PENDING:
                results.append(_proposal_to_out(pa))
                break

    # ── 研发总监: pending_director 状态 ──
    if not status or status == ProposalStatus.PENDING_DIRECTOR:
        director_query = db.query(ProposalApproval).filter(
            ProposalApproval.status == ProposalStatus.PENDING_DIRECTOR,
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
    if status and status in (ProposalStatus.APPROVED, ProposalStatus.REJECTED):
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
    action: str = Body(..., pattern=f"^({ReviewStatus.APPROVED}|{ReviewStatus.REJECTED})$"),
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
        if pa.status not in (ProposalStatus.PENDING_PARALLEL, ProposalStatus.PENDING_DIRECTOR):
            raise HTTPException(status_code=400, detail="当前不在审批阶段")

        if action == "rejected":
            _change_status(db, pa, ProposalStatus.REJECTED)
            _create_notification(
                db,
                target_user_id=pa.proposer_id,
                title=f"立项审批被管理员驳回: {pa.title}",
                content=f"管理员 {current_user.username} 驳回了项目「{pa.title}」的立项申请。"
                        + (f"原因: {reason}" if reason else ""),
            )
        else:  # approved
            _change_status(db, pa, ProposalStatus.APPROVED)

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
                project.approval_status = pa.status  # BUGFIX: 同步审批状态到Project表

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
        if pa.status != ProposalStatus.PENDING_PARALLEL:
            raise HTTPException(status_code=400, detail="当前不在并行审批阶段")

        # 原子更新：仅当该行 status='pending' 时才更新（防止并发覆盖）
        from sqlalchemy import update as sa_update
        stmt = (
            sa_update(ProposalParallelReviewer)
            .where(
                ProposalParallelReviewer.approval_id == pa.id,
                ProposalParallelReviewer.user_id == user_id,
                ProposalParallelReviewer.status == ReviewStatus.PENDING,
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
            if existing and existing.status != ReviewStatus.PENDING:
                raise HTTPException(status_code=400, detail="您已审批过该申请")
            else:
                raise HTTPException(status_code=400, detail="审批状态异常，请重试")
        db.flush()

        if action == "rejected":
            # 驳回 → 整个审批结束
            _change_status(db, pa, ProposalStatus.REJECTED)

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
                r.status == ReviewStatus.APPROVED for r in
                db.query(ProposalParallelReviewer)
                .filter(ProposalParallelReviewer.approval_id == pa.id)
                .all()
            )
            if all_approved:
                # 全部通过 → 进入研发总监审批
                _change_status(db, pa, ProposalStatus.PENDING_DIRECTOR)

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
        if pa.status != ProposalStatus.PENDING_DIRECTOR:
            raise HTTPException(status_code=400, detail="当前不在研发总监审批阶段")

        if pa.director_status != ReviewStatus.PENDING:
            raise HTTPException(status_code=400, detail="您已审批过该申请")

        pa.director_status = action
        pa.director_reason = reason
        pa.director_reviewed_at = now

        if action == "rejected":
            # 驳回
            _change_status(db, pa, ProposalStatus.REJECTED)

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
                project.approval_status = pa.status  # BUGFIX: 同步审批状态到Project表

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
            _change_status(db, pa, ProposalStatus.APPROVED)

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
            ProposalApproval.status.in_([ProposalStatus.PENDING_PARALLEL, ProposalStatus.PENDING_DIRECTOR]),
        )
        .first()
    )
    if not pa:
        raise HTTPException(status_code=400, detail="该项目没有进行中的审批，无法撤销")

    # ── 3. 恢复项目为草稿 ──
    p.is_draft = True
    p.status = "draft"

    # ── 4. 标记审批为撤销 ──
    _change_status(db, pa, ProposalStatus.WITHDRAWN)

    # ── 5. 同步 ApprovalRequest ──
    ar = db.query(ApprovalRequest).filter(
        ApprovalRequest.request_type == "proposal",
        ApprovalRequest.request_id == pa.id,
    ).first()
    if ar:
        ar.status = ApprovalRequestStatus.WITHDRAWN

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
