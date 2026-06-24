"""项目立项审批 - 辅助函数

导出:
    _validate_approver_config, _change_status, _project_to_snapshot,
    _proposal_to_out, _load_parallel_reviewers, _create_notification,
    _ensure_proposal_chain, _sync_approval_request, _parse_date, _apply_payload
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.proposal_approval import (
    ProposalApproval, ProposalParallelReviewer,
    ProposalStatus, ReviewStatus, ApprovalRequestStatus,
)
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest
from app.models.alert import Notification


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
    """变更 ProposalApproval 状态并同步 ApprovalRequest + Project.approval_status

    禁止在业务代码中直接写 pa.status = "..."，必须通过本函数。
    """
    pa.status = new_status
    _sync_approval_request(db, pa)

    # 同步 Project.approval_status（死字段修复）
    p: Project | None = db.query(Project).filter(Project.id == pa.proposal_id).first()
    if p:
        if new_status in (ProposalStatus.PENDING_PARALLEL, ProposalStatus.PENDING_DIRECTOR):
            p.approval_status = "pending"
        elif new_status == ProposalStatus.APPROVED:
            p.approval_status = "approved"
        elif new_status == ProposalStatus.REJECTED:
            p.approval_status = "rejected"


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
    """创建系统内通知记录（当前仅写入 notifications 表，未接入钉钉/飞书等外部渠道）

    TODO: 如需外部通知，在写入后添加 webhook 调用：
      - dingtalk: httpx.post(webhook_url, json={"msgtype": "markdown", ...})
      - feishu: httpx.post(webhook_url, json={"msg_type": "post", ...})
    """
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
# 辅助: 同步 ApprovalRequest（供通用审批列表查询）
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
        ProposalStatus.PENDING_PARALLEL: ApprovalRequestStatus.PENDING,
        ProposalStatus.PENDING_DIRECTOR: ApprovalRequestStatus.PENDING,
        ProposalStatus.APPROVED: ApprovalRequestStatus.APPROVED,
        ProposalStatus.REJECTED: ApprovalRequestStatus.REJECTED,
        ProposalStatus.WITHDRAWN: ApprovalRequestStatus.WITHDRAWN,
    }
    new_status = status_map.get(pa.status, ApprovalRequestStatus.PENDING)
    if ar.status != new_status:
        ar.status = new_status


# ══════════════════════════════════════════════════════════════════
# 辅助: 日期解析
# ══════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════
# 辅助: 应用 payload
# ══════════════════════════════════════════════════════════════════

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
