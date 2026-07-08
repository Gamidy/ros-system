"""ECO明细项管理 API — 从 eco.py 拆分""" 
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.core.enums import ECOStatus
from app.models.user import User
from app.models.ecr_eco import ECO, ECOItem
from app.schemas import ECOItemCreate, ECOItemUpdate, ECOItemOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eco", tags=["ECO"])


# ── 辅助函数（从 eco.py 共享） ──────────────────────────────


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


def _item_to_out(item: ECOItem) -> ECOItemOut:
    """ECOItem ORM对象 → ECOItemOut dict"""
    return ECOItemOut(
        id=item.id,
        eco_id=item.eco_id,
        seq=item.seq,
        change_type=item.change_type,
        object_type=item.object_type,
        object_id=item.object_id,
        object_code=item.object_code,
        object_name=item.object_name,
        old_value=item.old_value,
        new_value=item.new_value,
        description=item.description,
        created_at=item.created_at,
    )


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
