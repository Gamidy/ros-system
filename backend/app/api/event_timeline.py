"""事件时间线 API — 分页查询、Saga链追踪、快照差异对比、重放、统计

权限规则:
- GET 系列: 仅需登录 (Depends(get_current_user))
- POST 系列: 需 pm 或 admin 角色 (require_role(['pm','admin']))
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.event_store import EventStore
from app.core.saga_engine import saga_coordinator
from app.core.security import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/events", tags=["事件时间线"])


# ════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════





# ════════════════════════════════════════════════════════
# GET /api/v2/events/timeline/{plan_id} — 分页事件时间线
# ════════════════════════════════════════════════════════


@router.get("/timeline/{plan_id}")
def get_paginated_timeline(
    plan_id: str,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数(最大200)"),
    event_type: Optional[str] = Query(None, description="按事件类型过滤"),
    status: Optional[str] = Query(None, description="按事件状态过滤(emitted/processed/failed)"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    """获取事件时间线（分页版）

    支持按 event_type 和 status 过滤，返回分页数据。
    """
    result = EventStore.paginated_timeline(
        plan_id=plan_id,
        page=page,
        page_size=page_size,
        event_type=event_type,
        status=status,
        db=db,
    )
    return {
        "plan_id": plan_id,
        **result,
    }


# ════════════════════════════════════════════════════════
# GET /api/v2/events/timeline/{plan_id}/detail — 完整事件列表含快照差异
# ════════════════════════════════════════════════════════


@router.get("/timeline/{plan_id}/detail")
def get_timeline_detail(
    plan_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    """获取事件时间线详情（含每个事件的快照差异对比）

    返回分页事件列表，每个事件附带其相对于上一个事件的 state_snapshot 差异。
    """
    result = EventStore.paginated_timeline(
        plan_id=plan_id,
        page=page,
        page_size=page_size,
        db=db,
    )
    # 为每个事件附加快照差异
    detail_items = []
    for item in result["items"]:
        event_id = item["id"]
        diff = EventStore.get_snapshot_diff_for_event(event_id, db=db)
        detail_items.append({
            **item,
            "snapshot_diff": diff["diff"] if diff else [],
        })
    return {
        "plan_id": plan_id,
        "items": detail_items,
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


# ════════════════════════════════════════════════════════
# GET /api/v2/events/saga/{saga_id} — 查询Saga步骤链
# ════════════════════════════════════════════════════════


@router.get("/saga/{saga_id}")
def get_saga_detail(
    saga_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    """查询 Saga 事务的完整步骤链

    从 event_logs 中按 saga_id 查询所有关联事件，
    同时返回 SagaCoordinator 内存中的执行结果（如有）。
    """
    # 从事件日志获取 Saga 步骤链
    chain = EventStore.get_saga_chain(saga_id, db=db)

    # 从 SagaCoordinator 获取内存结果
    mem_result = saga_coordinator.get_result(saga_id)
    saga_status = mem_result.to_dict() if mem_result else None

    return {
        "saga_id": saga_id,
        "event_chain": chain,
        "event_count": len(chain),
        "saga_result": saga_status,
    }


# ════════════════════════════════════════════════════════
# POST /api/v2/events/replay/{plan_id} — 重放事件（含快照差异对比）
# ════════════════════════════════════════════════════════


@router.post("/replay/{plan_id}")
def replay_plan_events_with_diff(
    plan_id: str,
    until_event_id: Optional[int] = Query(None, description="重放到指定事件ID为止（可选）"),
    db: Session = Depends(get_db),
    _=Depends(require_role("pm", "admin")),
) -> dict:
    """重放 ProductPlan 事件，重建最终状态并附带快照差异对比

    权限: pm, admin
    """
    # 先获取当前完整事件列表（用于 diff 计算）
    raw_timeline = EventStore.get_timeline(plan_id, db=db, limit=50000)

    # 执行重放
    success, state = EventStore.replay(plan_id, until_event_id=until_event_id, db=db)

    if not success:
        raise HTTPException(status_code=404, detail=state.get("error", "重放失败"))

    # 计算事件间快照差异（仅对有 state_snapshot 的事件）
    snapshot_diffs = []
    prev_snapshot: Optional[dict] = None
    for evt in raw_timeline:
        if evt.get("state_snapshot") is not None:
            cur_snapshot = evt["state_snapshot"]
            diff_fields = []
            if prev_snapshot is not None:
                all_keys = set(list(prev_snapshot.keys()) + list(cur_snapshot.keys()))
                for key in sorted(all_keys):
                    old_val = prev_snapshot.get(key)
                    new_val = cur_snapshot.get(key)
                    if old_val != new_val:
                        diff_fields.append({
                            "field": key,
                            "before": old_val,
                            "after": new_val,
                        })
            snapshot_diffs.append({
                "event_id": evt["id"],
                "event_type": evt["event_type"],
                "created_at": evt["created_at"],
                "diff": diff_fields,
            })
            prev_snapshot = cur_snapshot

    return {
        "success": True,
        "plan_id": plan_id,
        "state": state,
        "replay_info": {
            "total_events": len(raw_timeline),
            "snapshot_diffs": snapshot_diffs,
        },
    }


# ════════════════════════════════════════════════════════
# GET /api/v2/events/stats — 事件统计概览
# ════════════════════════════════════════════════════════


@router.get("/stats")
def get_event_stats(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    """事件统计概览

    返回:
    - total_events: 总事件数
    - by_status: 按状态分组统计
    - by_event_type: 按事件类型分组统计（Top 20）
    - by_date: 近7天每日事件数
    - top_plans: 事件最多的 plan_id Top 10
    """
    stats = {}

    # 总事件数
    total = db.execute(text("SELECT COUNT(*) FROM event_logs")).scalar() or 0
    stats["total_events"] = total

    # 按状态统计
    status_rows = db.execute(
        text("SELECT status, COUNT(*) as cnt FROM event_logs GROUP BY status ORDER BY cnt DESC")
    ).fetchall()
    stats["by_status"] = {r[0]: r[1] for r in status_rows}

    # 按事件类型统计 (Top 20)
    type_rows = db.execute(
        text("""
            SELECT event_type, COUNT(*) as cnt
            FROM event_logs
            GROUP BY event_type
            ORDER BY cnt DESC
            LIMIT 20
        """)
    ).fetchall()
    stats["by_event_type"] = {r[0]: r[1] for r in type_rows}
    seven_days_ago = datetime.now() - timedelta(days=7)
    day_rows = db.execute(
        text("""
            SELECT DATE(created_at) as d, COUNT(*) as cnt
            FROM event_logs
            WHERE created_at >= :seven_days_ago
            GROUP BY DATE(created_at)
            ORDER BY d ASC
        """),
        {"seven_days_ago": seven_days_ago},
    ).fetchall()
    stats["by_date"] = {str(r[0]): r[1] for r in day_rows}

    # 事件最多的 plan_id Top 10
    plan_rows = db.execute(
        text("""
            SELECT plan_id, COUNT(*) as cnt
            FROM event_logs
            WHERE plan_id IS NOT NULL
            GROUP BY plan_id
            ORDER BY cnt DESC
            LIMIT 10
        """)
    ).fetchall()
    stats["top_plans"] = [{"plan_id": r[0], "count": r[1]} for r in plan_rows]

    # Saga 统计
    saga_total = db.execute(
        text("SELECT COUNT(DISTINCT saga_id) FROM event_logs WHERE saga_id IS NOT NULL")
    ).scalar() or 0
    stats["total_sagas"] = saga_total

    return stats
