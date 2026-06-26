"""ECO API模块 — 工程变更指令 CRUD + 状态转换 + 明细项管理 + 变更看板"""
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.core.enums import ECOStatus
from app.models.user import User
from app.models.ecr_eco import ECO, ECOItem, ECRRequest
from app.schemas import (
    ECOCreate, ECOUpdate, ECOOut, ECODetailOut,
    ECOItemCreate, ECOItemUpdate, ECOItemOut,
    ECOChDashboardOut,
)

router = APIRouter(prefix="/api/eco", tags=["ECO"])


# ══════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════

def _gen_eco_code(db: Session) -> str:
    """生成ECO编号: ECO-YYYYMMDD-XXXX (每日自增序号)"""
    today_str = date.today().strftime("%Y%m%d")
    prefix = f"ECO-{today_str}-"
    last = (
        db.query(ECO)
        .filter(ECO.code.like(f"{prefix}%"))
        .order_by(ECO.code.desc())
        .first()
    )
    seq = (int(last.code[-4:]) + 1) if last else 1
    return f"{prefix}{seq:04d}"


def _get_eco_or_404(db: Session, eco_id: int) -> ECO:
    """按ID查找ECO，不存在则404"""
    eco = db.query(ECO).filter(ECO.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO不存在")
    return eco


def _check_status(eco: ECO, allowed: list[str], action: str = "操作"):
    """检查ECO当前状态是否允许指定操作"""
    if eco.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"ECO当前状态为'{eco.status}'，不允许{action}（允许: {'/'.join(allowed)}）",
        )


def _count_items(db: Session, eco_id: int) -> int:
    """查询ECO的明细项数量"""
    return db.query(func.count(ECOItem.id)).filter(ECOItem.eco_id == eco_id).scalar() or 0


def _eco_to_out(eco: ECO, db: Optional[Session] = None) -> dict:
    """ECO ORM对象 → ECOOut dict"""
    return {
        "id": eco.id,
        "code": eco.code,
        "ecr_id": eco.ecr_id,
        "title": eco.title,
        "change_summary": eco.change_summary,
        "implementation_plan": eco.implementation_plan,
        "effective_date": eco.effective_date,
        "status": eco.status,
        "created_by": eco.created_by,
        "verified_by": eco.verified_by,
        "verified_at": eco.verified_at,
        "closed_by": eco.closed_by,
        "closed_at": eco.closed_at,
        "org_id": eco.org_id,
        "created_at": eco.created_at,
        "updated_at": eco.updated_at,
        "item_count": _count_items(db, eco.id) if db else (len(eco.items) if hasattr(eco, "items") and eco.items else 0),
    }


def _eco_to_detail(eco: ECO, db: Session) -> dict:
    """ECO ORM对象 → ECODetailOut dict（含明细项+关联ECR信息）"""
    items_out = []
    for item in (eco.items or []):
        items_out.append({
            "id": item.id,
            "eco_id": item.eco_id,
            "seq": item.seq,
            "change_type": item.change_type,
            "object_type": item.object_type,
            "object_id": item.object_id,
            "object_code": item.object_code,
            "object_name": item.object_name,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "description": item.description,
            "created_at": item.created_at,
        })

    base = _eco_to_out(eco, db)
    base["items"] = items_out
    base["ecr_code"] = eco.ecr.code if eco.ecr else None
    base["ecr_title"] = eco.ecr.title if eco.ecr else None
    return base


def _item_to_out(item: ECOItem) -> dict:
    """ECOItem ORM对象 → ECOItemOut dict"""
    return {
        "id": item.id,
        "eco_id": item.eco_id,
        "seq": item.seq,
        "change_type": item.change_type,
        "object_type": item.object_type,
        "object_id": item.object_id,
        "object_code": item.object_code,
        "object_name": item.object_name,
        "old_value": item.old_value,
        "new_value": item.new_value,
        "description": item.description,
        "created_at": item.created_at,
    }


# ══════════════════════════════════════════════════
# 变更看板（必须在 /{eco_id} 路由之前定义）
# ══════════════════════════════════════════════════

@router.get("/changes", response_model=ECOChDashboardOut)
def eco_changes_dashboard(
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOChDashboardOut:
    """ECO变更看板: 按状态统计 + 按类型分布 + 本月新增 + 待验证 + 最近变更"""
    # 按状态统计
    status_rows = db.query(ECO.status, func.count(ECO.id)).group_by(ECO.status).all()
    status_summary = {row[0]: row[1] for row in status_rows}

    # 按变更类型分布（从ECOItem的change_type统计）
    type_rows = db.query(ECOItem.change_type, func.count(ECOItem.id)).group_by(ECOItem.change_type).all()
    type_distribution = {row[0]: row[1] for row in type_rows}

    # 本月新增
    first_day = date.today().replace(day=1)
    this_month_new = (
        db.query(func.count(ECO.id))
        .filter(cast(ECO.created_at, Date) >= first_day)
        .scalar()
    ) or 0

    # 待验证（IMPLEMENTING状态的ECO）
    pending_verification = (
        db.query(func.count(ECO.id))
        .filter(ECO.status == ECOStatus.IMPLEMENTING.value)
        .scalar()
    ) or 0

    # 最近10条变更
    recent = (
        db.query(ECO)
        .order_by(ECO.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "status_summary": status_summary,
        "type_distribution": type_distribution,
        "this_month_new": this_month_new,
        "pending_verification": pending_verification,
        "changes": [_eco_to_out(eco, db) for eco in recent],
    }


# ══════════════════════════════════════════════════
# ECO CRUD
# ══════════════════════════════════════════════════

@router.get("", response_model=list[ECOOut])
def list_ecos(
    status: Optional[str] = Query(None, description="按状态过滤"),
    keyword: Optional[str] = Query(None, description="按标题/编号/摘要搜索"),
    date_from: Optional[date] = Query(None, description="起始日期(created_at)"),
    date_to: Optional[date] = Query(None, description="截止日期(created_at)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> list[ECOOut]:
    """ECO列表查询 — 支持状态/关键词/日期范围过滤及分页"""
    q = db.query(ECO)

    if status:
        q = q.filter(ECO.status == status)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            ECO.code.ilike(kw)
            | ECO.title.ilike(kw)
            | ECO.change_summary.ilike(kw),
        )
    if date_from:
        q = q.filter(cast(ECO.created_at, Date) >= date_from)
    if date_to:
        q = q.filter(cast(ECO.created_at, Date) <= date_to)

    items = (
        q.order_by(ECO.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [_eco_to_out(eco, db) for eco in items]


@router.post("", response_model=ECOOut, status_code=201)
def create_eco(
    data: ECOCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """创建ECO — 自动生成编号，可同时创建明细项"""
    # 校验关联ECR
    if data.ecr_id is not None:
        ecr = db.query(ECRRequest).filter(ECRRequest.id == data.ecr_id).first()
        if not ecr:
            raise HTTPException(status_code=404, detail="关联ECR不存在")

    code = _gen_eco_code(db)

    eco = ECO(
        code=code,
        ecr_id=data.ecr_id,
        title=data.title,
        change_summary=data.change_summary,
        implementation_plan=data.implementation_plan,
        effective_date=data.effective_date,
        status=ECOStatus.DRAFT.value,
        created_by=current_user.id,
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(eco)
    db.flush()

    # 批量创建明细项
    for idx, item in enumerate(data.items or []):
        db.add(ECOItem(
            eco_id=eco.id,
            seq=idx + 1,
            change_type=item.change_type,
            object_type=item.object_type,
            object_id=item.object_id,
            object_code=item.object_code,
            object_name=item.object_name,
            old_value=item.old_value,
            new_value=item.new_value,
            description=item.description,
            org_id=getattr(current_user, "org_id", None),
        ))

    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.get("/{eco_id}", response_model=ECODetailOut)
def get_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECODetailOut:
    """获取ECO详情 — 含明细项列表 + 关联ECR信息"""
    eco = (
        db.query(ECO)
        .options(joinedload(ECO.items), joinedload(ECO.ecr))
        .filter(ECO.id == eco_id)
        .first()
    )
    if not eco:
        raise HTTPException(status_code=404, detail="ECO不存在")
    return _eco_to_detail(eco, db)


@router.put("/{eco_id}", response_model=ECOOut)
def update_eco(
    eco_id: int,
    data: ECOUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """更新ECO基本信息 — 仅DRAFT状态允许"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value], "更新")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(eco, key, val)
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.delete("/{eco_id}", status_code=204)
def delete_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> None:
    """删除ECO — 仅DRAFT状态允许（级联删除明细项）"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value], "删除")
    db.delete(eco)
    db.commit()


# ══════════════════════════════════════════════════
# 状态转换
# ══════════════════════════════════════════════════

@router.post("/{eco_id}/implement", response_model=ECOOut)
def implement_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """开始实施: DRAFT → IMPLEMENTING"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value], "开始实施")
    eco.status = ECOStatus.IMPLEMENTING.value
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.post("/{eco_id}/verify", response_model=ECOOut)
def verify_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """验证通过: IMPLEMENTING → VERIFIED，记录验证人/验证时间"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.IMPLEMENTING.value], "验证")
    now = datetime.now(timezone.utc)
    eco.status = ECOStatus.VERIFIED.value
    eco.verified_by = current_user.id
    eco.verified_at = now
    eco.updated_at = now
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.post("/{eco_id}/effective", response_model=ECOOut)
def effective_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """生效: VERIFIED → EFFECTIVE（预留BOM联动接口）"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.VERIFIED.value], "生效")
    eco.status = ECOStatus.EFFECTIVE.value
    eco.updated_at = datetime.now(timezone.utc)
    # TODO: BOM联动 — eco_bom_service.on_eco_effective(eco.id)
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.post("/{eco_id}/close", response_model=ECOOut)
def close_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """关闭: EFFECTIVE → CLOSED，记录关闭人/关闭时间"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.EFFECTIVE.value], "关闭")
    now = datetime.now(timezone.utc)
    eco.status = ECOStatus.CLOSED.value
    eco.closed_by = current_user.id
    eco.closed_at = now
    eco.updated_at = now
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.post("/{eco_id}/cancel", response_model=ECOOut)
def cancel_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """取消: 任意状态 → CANCELLED（已关闭/已取消状态的ECO不可取消）"""
    eco = _get_eco_or_404(db, eco_id)
    if eco.status in (ECOStatus.CLOSED.value, ECOStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail=f"ECO已处于'{eco.status}'状态，无法取消")
    eco.status = ECOStatus.CANCELLED.value
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


# ══════════════════════════════════════════════════
# 明细项管理
# ══════════════════════════════════════════════════

@router.post("/{eco_id}/items", response_model=ECOItemOut, status_code=201)
def add_eco_item(
    eco_id: int,
    data: ECOItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOItemOut:
    """新增ECO明细项 — 仅DRAFT/IMPLEMENTING状态允许"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value, ECOStatus.IMPLEMENTING.value], "新增明细项")

    max_seq = (
        db.query(func.coalesce(func.max(ECOItem.seq), 0))
        .filter(ECOItem.eco_id == eco_id)
        .scalar()
    ) or 0

    item = ECOItem(
        eco_id=eco.id,
        seq=max_seq + 1,
        change_type=data.change_type,
        object_type=data.object_type,
        object_id=data.object_id,
        object_code=data.object_code,
        object_name=data.object_name,
        old_value=data.old_value,
        new_value=data.new_value,
        description=data.description,
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_out(item)


@router.put("/{eco_id}/items/{item_id}", response_model=ECOItemOut)
def update_eco_item(
    eco_id: int,
    item_id: int,
    data: ECOItemUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOItemOut:
    """更新ECO明细项 — 仅DRAFT/IMPLEMENTING状态允许"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value, ECOStatus.IMPLEMENTING.value], "更新明细项")

    item = db.query(ECOItem).filter(ECOItem.id == item_id, ECOItem.eco_id == eco_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="明细项不存在")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    db.commit()
    db.refresh(item)
    return _item_to_out(item)


@router.delete("/{eco_id}/items/{item_id}", status_code=204)
def delete_eco_item(
    eco_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> None:
    """删除ECO明细项 — 仅DRAFT/IMPLEMENTING状态允许"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value, ECOStatus.IMPLEMENTING.value], "删除明细项")

    item = db.query(ECOItem).filter(ECOItem.id == item_id, ECOItem.eco_id == eco_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="明细项不存在")
    db.delete(item)
    db.commit()
