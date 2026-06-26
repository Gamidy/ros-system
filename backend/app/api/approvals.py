"""审批流API: 审批链管理 + 审批请求提交流程"""
import copy
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.user import User
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest, ApprovalRecord
from app.schemas import (
    ApprovalChainCreate, ApprovalChainOut,
    ApprovalStepCreate, ApprovalStepOut,
    ApprovalRequestCreate, ApprovalRequestOut,
    ApprovalRecordOut, ApprovalDecision,
)

router = APIRouter(prefix="/approval", tags=["审批流"])


# ══════════════════════════════════════════════════
# 默认审批链初始化
# ══════════════════════════════════════════════════

DEFAULT_CHAINS = [
    {
        "name": "账号申请审批",
        "code": "account_register",
        "description": "新账号注册审批流程",
        "steps": [
            {"seq": 1, "role": "个人", "name": "申请人提交"},
            {"seq": 2, "role": "研发总监", "name": "研发总监审批"},
        ],
    },
    {
        "name": "ECR审批",
        "code": "ecr",
        "description": "工程变更请求审批流程",
        "steps": [
            {"seq": 1, "role": "工程师", "name": "工程师提交"},
            {"seq": 2, "role": "模块经理", "name": "模块经理审批"},
            {"seq": 3, "role": "研发总监", "name": "研发总监审批"},
        ],
    },
    {
        "name": "立项审批",
        "code": "proposal",
        "description": "产品立项审批流程（并行审批 + 研发总监终审）",
        "steps": [
            {"seq": 1, "role": "产品经理", "name": "产品经理提交", "step_type": "sequential"},
            {"seq": 2, "role": "并行审批人", "name": "模块经理/工程师并行审批", "step_type": "parallel"},
            {"seq": 3, "role": "研发总监", "name": "研发总监终审", "step_type": "sequential"},
        ],
    },
    {
        "name": "采购审批",
        "code": "purchase",
        "description": "采购申请审批流程",
        "steps": [
            {"seq": 1, "role": "采购", "name": "采购提交"},
            {"seq": 2, "role": "模块经理", "name": "模块经理审批"},
            {"seq": 3, "role": "总经理", "name": "总经理审批"},
        ],
    },
]


def _ensure_default_chains(db: Session):
    """确保默认审批链存在"""
    for chain_data in DEFAULT_CHAINS:
        existing = db.query(ApprovalChain).filter(ApprovalChain.code == chain_data["code"]).first()
        if not existing:
            chain = ApprovalChain(
                name=chain_data["name"],
                code=chain_data["code"],
                description=chain_data["description"],
            )
            db.add(chain)
            db.flush()
            for step in chain_data["steps"]:
                db.add(ApprovalStep(
                    chain_id=chain.id,
                    seq=step["seq"],
                    role=step["role"],
                    name=step["name"],
                    step_type=step.get("step_type", "sequential"),
                ))
    db.commit()


# ══════════════════════════════════════════════════
# 审批链管理
# ══════════════════════════════════════════════════

@router.get("/chains", response_model=list[ApprovalChainOut])
def list_approval_chains(db: Session = Depends(get_db), _=Depends(require_menu("approvals"))) -> list[ApprovalChainOut]:
    """列出所有审批链（含步骤）"""
    _ensure_default_chains(db)
    chains = db.query(ApprovalChain).order_by(ApprovalChain.id).all()
    return [_chain_to_out(c) for c in chains]


@router.post("/chains", response_model=ApprovalChainOut)
def create_approval_chain(
    data: ApprovalChainCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager")),
) -> ApprovalChainOut:
    """创建审批链（需要admin角色）"""
    if db.query(ApprovalChain).filter(ApprovalChain.code == data.code).first():
        raise HTTPException(status_code=400, detail="审批链编码已存在")

    chain = ApprovalChain(
        name=data.name,
        code=data.code,
        description=data.description,
    )
    db.add(chain)
    db.flush()

    for step in (data.steps or []):
        db.add(ApprovalStep(
            chain_id=chain.id,
            seq=step.seq,
            role=step.role,
            name=step.name,
            step_type=step.step_type or "sequential",
        ))
    db.commit()
    db.refresh(chain)
    return _chain_to_out(chain)


@router.get("/chains/{chain_id}", response_model=ApprovalChainOut)
def get_approval_chain(chain_id: int, db: Session = Depends(get_db), _=Depends(require_menu("approvals"))) -> ApprovalChainOut:
    """查看审批链详情"""
    chain = db.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="审批链不存在")
    return _chain_to_out(chain)


# ══════════════════════════════════════════════════
# 审批请求
# ══════════════════════════════════════════════════

@router.post("/requests", response_model=ApprovalRequestOut)
def submit_approval_request(
    data: ApprovalRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager", "rd_director", "module_manager", "module_manager_struct", "module_manager_sys", "procurement_director", "process_manager", "project_admin")),
) -> ApprovalRequestOut:
    """提交审批请求"""
    chain = db.query(ApprovalChain).filter(ApprovalChain.id == data.chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="审批链不存在")

    request = ApprovalRequest(
        chain_id=data.chain_id,
        request_type=data.request_type,
        request_id=data.request_id,
        title=data.title,
        requester=data.requester or current_user.username,
        status="pending",
        current_step=1,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return _request_to_out(request, db)


@router.get("/requests", response_model=list[ApprovalRequestOut])
def list_approval_requests(
    status: Optional[str] = None,
    requester: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_menu("approvals")),
) -> list[ApprovalRequestOut]:
    """列出审批请求，支持按status/requester过滤"""
    from app.core.permissions import is_super_role
    q = db.query(ApprovalRequest)
    if status:
        q = q.filter(ApprovalRequest.status == status)
    if requester:
        q = q.filter(ApprovalRequest.requester == requester)
    elif not status and not requester:
        # admin/general_manager 默认查看全部，其他角色默认只看自己的
        if not is_super_role(current_user.role):
            q = q.filter(ApprovalRequest.requester == current_user.username)
    q = q.order_by(ApprovalRequest.created_at.desc())
    return [_request_to_out(r, db) for r in q.limit(200).all()]


@router.get("/requests/pending", response_model=list[ApprovalRequestOut])
def list_pending_approval_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_menu("approvals")),
) -> list[ApprovalRequestOut]:
    """待我审批的列表（按当前用户角色匹配当前步骤的角色）"""
    from app.core.permissions import is_super_role
    _ensure_default_chains(db)
    pending = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == "pending"
    ).order_by(ApprovalRequest.created_at.desc()).limit(200).all()

    result = []
    for req in pending:
        # admin/general_manager 可以看到所有待审批项
        if is_super_role(current_user.role):
            result.append(_request_to_out(req, db))
            continue
        steps = db.query(ApprovalStep).filter(
            ApprovalStep.chain_id == req.chain_id,
            ApprovalStep.seq == req.current_step,
        ).all()
        if any(s.role == current_user.role for s in steps):
            result.append(_request_to_out(req, db))
            continue
        # 并行步骤：检查 step_meta 中的 required_roles
        meta = _get_step_meta(req, req.current_step)
        if meta and current_user.role in meta.get("required_roles", []):
            result.append(_request_to_out(req, db))
    return result


@router.get("/requests/{request_id}", response_model=ApprovalRequestOut)
def get_approval_request(
    request_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("approvals")),
) -> ApprovalRequestOut:
    """查看审批请求详情"""
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return _request_to_out(req, db)


@router.post("/requests/{request_id}/approve", response_model=ApprovalRequestOut)
def approve_approval_request(
    request_id: int,
    decision: ApprovalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager", "rd_director", "module_manager", "module_manager_struct", "module_manager_sys", "procurement_director", "process_manager", "project_admin")),
) -> ApprovalRequestOut:
    """审批通过"""
    return _make_decision(request_id, "approved", decision, db, current_user)


@router.post("/requests/{request_id}/reject", response_model=ApprovalRequestOut)
def reject_approval_request(
    request_id: int,
    decision: ApprovalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "general_manager", "rd_director", "module_manager", "module_manager_struct", "module_manager_sys", "procurement_director", "process_manager", "project_admin")),
) -> ApprovalRequestOut:
    """审批驳回"""
    return _make_decision(request_id, "rejected", decision, db, current_user)


# ══════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════

def _chain_to_out(chain: ApprovalChain) -> dict:
    """将ApprovalChain ORM对象转为输出dict"""
    return {
        "id": chain.id,
        "name": chain.name,
        "code": chain.code,
        "description": chain.description,
        "steps": [
            {
                "id": s.id,
                "chain_id": s.chain_id,
                "seq": s.seq,
                "role": s.role,
                "name": s.name,
                "step_type": s.step_type or "sequential",
                "created_at": s.created_at,
            }
            for s in sorted(chain.step_items or [], key=lambda x: x.seq)
        ],
        "created_at": chain.created_at,
    }


def _request_to_out(req: ApprovalRequest, db: Session) -> dict:
    """将ApprovalRequest ORM对象转为输出dict（含步骤和记录）"""
    steps = db.query(ApprovalStep).filter(
        ApprovalStep.chain_id == req.chain_id
    ).order_by(ApprovalStep.seq).all()

    records = db.query(ApprovalRecord).filter(
        ApprovalRecord.request_id == req.id
    ).order_by(ApprovalRecord.decided_at).all()

    return {
        "id": req.id,
        "chain_id": req.chain_id,
        "request_type": req.request_type,
        "request_id": req.request_id,
        "title": req.title,
        "requester": req.requester,
        "status": req.status,
        "current_step": req.current_step,
        "step_meta": req.step_meta,
        "steps": [
            {
                "id": s.id,
                "chain_id": s.chain_id,
                "seq": s.seq,
                "role": s.role,
                "name": s.name,
                "step_type": s.step_type or "sequential",
                "created_at": s.created_at,
            }
            for s in steps
        ],
        "records": [
            {
                "id": r.id,
                "request_id": r.request_id,
                "step_id": r.step_id,
                "approver": r.approver,
                "decision": r.decision,
                "comment": r.comment,
                "decided_at": r.decided_at,
            }
            for r in records
        ],
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }


def _make_decision(
    request_id: int,
    action: str,
    decision: ApprovalDecision,
    db: Session,
    current_user: User,
) -> dict:
    """执行审批决策（通过/驳回）—— 支持 sequential 和 parallel 步骤类型"""
    from app.core.permissions import is_super_role
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="该请求已审批完成")

    # 查询当前步骤
    steps = db.query(ApprovalStep).filter(
        ApprovalStep.chain_id == req.chain_id,
        ApprovalStep.seq == req.current_step,
    ).all()
    if not steps:
        raise HTTPException(status_code=400, detail="当前步骤配置不存在")

    current_step_obj = steps[0]
    step_type = current_step_obj.step_type or "sequential"

    # 检查权限（超级角色可以审批任意步骤）
    if not is_super_role(current_user.role):
        if step_type == "parallel":
            # 并行步骤：检查用户角色是否在 step_meta 的 required_roles 中
            meta = _get_step_meta(req, req.current_step)
            if not meta or current_user.role not in meta.get("required_roles", []):
                raise HTTPException(status_code=403, detail="您不是当前并行审批步骤的审批人")
            # 检查是否已审批过（防止同一人多次操作）
            if current_user.username in (meta.get("decisions") or {}):
                raise HTTPException(status_code=400, detail="您已审批过该申请")
        else:
            # 顺序步骤：检查用户角色是否匹配步骤角色
            if not any(s.role == current_user.role for s in steps):
                raise HTTPException(status_code=403, detail="您不是当前审批步骤的审批人")

    step_id = steps[0].id if steps else None

    # 创建审批记录
    record = ApprovalRecord(
        request_id=req.id,
        step_id=step_id,
        approver=current_user.username,
        decision=action,
        comment=decision.comment,
    )
    db.add(record)

    if step_type == "parallel":
        # ── 并行步骤处理 ──
        meta = _get_step_meta(req, req.current_step)
        if meta is None:
            meta = {}
        if "decisions" not in meta:
            meta["decisions"] = {}
        meta["decisions"][current_user.username] = {
            "decision": action,
            "comment": decision.comment,
            "role": current_user.role,
        }
        _set_step_meta(req, req.current_step, meta)

        if action == "rejected":
            req.status = "rejected"
        else:
            # 检查所有 required_roles 是否都已 approved（按角色过滤）
            all_approved = all(
                any(
                    d.get("decision") == "approved"
                    for d in meta.get("decisions", {}).values()
                    if d.get("role") == role
                )
                for role in meta.get("required_roles", [])
            )
            if all_approved:
                _advance_to_next_step(req, db)
    else:
        # ── 顺序步骤处理（原有逻辑）──
        if action == "rejected":
            req.status = "rejected"
        else:
            _advance_to_next_step(req, db)

    db.commit()
    db.refresh(req)
    return _request_to_out(req, db)


def _advance_to_next_step(req: ApprovalRequest, db: Session):
    """将审批流转到下一步，或标记为通过"""
    next_step = db.query(ApprovalStep).filter(
        ApprovalStep.chain_id == req.chain_id,
        ApprovalStep.seq == req.current_step + 1,
    ).first()
    if next_step:
        req.current_step = next_step.seq
    else:
        req.status = "approved"


def _get_step_meta(req: ApprovalRequest, step_seq: int) -> dict | None:
    """获取指定步骤的并行审批元数据"""
    if not req.step_meta:
        return None
    return req.step_meta.get(str(step_seq))


def _set_step_meta(req: ApprovalRequest, step_seq: int, meta: dict):
    """设置指定步骤的并行审批元数据（深拷贝触发 SQLAlchemy dirty flag）"""
    if not req.step_meta:
        req.step_meta = {}
    modified = copy.deepcopy(req.step_meta)
    modified[str(step_seq)] = meta
    req.step_meta = modified
