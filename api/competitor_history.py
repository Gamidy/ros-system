"""竞品历史版本管理 API — 快照 & 变更记录 & 事件发射"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.competitor import CompetitorModel
from app.models.competitor_version import CompetitorVersion
from app.services import event_bus
# 从竞品主模块引入快照辅助函数
from app.api.competitor import _build_snapshot_data, _create_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pm", tags=["竞品库-历史版本"])


# ── 版本快照 / 历史变更 ────────────────────────────────────────────

@router.post("/competitors/{cid}/snapshot")
def take_snapshot(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """手动记录当前竞品参数快照"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")

    # 获取上次快照用于计算差异
    last_version = (
        db.query(CompetitorVersion)
        .filter(CompetitorVersion.competitor_id == cid)
        .order_by(CompetitorVersion.created_at.desc())
        .first()
    )
    old_snapshot = last_version.snapshot_data if last_version else None
    changed_by = current_user.username if hasattr(current_user, "username") else str(current_user.id)

    version = _create_snapshot(db, item, old_snapshot, changed_by)
    db.commit()
    db.refresh(version)

    return {
        "id": version.id,
        "competitor_id": version.competitor_id,
        "changed_fields": version.changed_fields,
        "changed_by": version.changed_by,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.get("/competitors/{cid}/history")
def get_competitor_history(
    cid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """查看竞品的历史变更记录"""
    item = db.query(CompetitorModel).filter(CompetitorModel.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="竞品记录不存在")

    versions = (
        db.query(CompetitorVersion)
        .filter(CompetitorVersion.competitor_id == cid)
        .order_by(CompetitorVersion.created_at.desc())
        .all()
    )

    return {
        "competitor_id": cid,
        "competitor": f"{item.brand} {item.model}",
        "total": len(versions),
        "versions": [
            {
                "id": v.id,
                "changed_fields": v.changed_fields,
                "snapshot_data": v.snapshot_data,
                "changed_by": v.changed_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


# ══════════════════════════════════════════════════
# Event Bus 发射点（供其他模块调用）
# ══════════════════════════════════════════════════

def emit_crawl_completed(
    market_code: str,
    brand: str,
    new_added: int = 0,
    updated: int = 0,
    skipped: int = 0,
    crawl_log_id: int | None = None,
) -> str:
    """发射 competitor.crawl_completed 事件"""
    return event_bus.emit(
        event_type="competitor.crawl_completed",
        payload={
            "market_code": market_code,
            "brand": brand,
            "new_added": new_added,
            "updated": updated,
            "skipped": skipped,
            "crawl_log_id": crawl_log_id,
        },
        source="competitor",
        producer="competitor.service",
    )


def emit_import_completed(
    market: str,
    total: int,
    success: int,
    failed: int,
    filename: str,
    user_id: str | None = None,
) -> str:
    """发射 competitor.imported 事件"""
    return event_bus.emit(
        event_type="competitor.imported",
        payload={
            "market": market,
            "total": total,
            "success": success,
            "failed": failed,
            "filename": filename,
        },
        source="competitor",
        producer="competitor.service",
        user_id=user_id,
    )
