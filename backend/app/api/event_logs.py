"""Event Log 管理 API — 事件日志查询与事件类型枚举

提供事件日志的列表、详情和事件类型枚举。
所有端点需要 admin 或 quality_engineer 角色。
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.event_log import EventLog
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["事件日志"])


def _safe_iso(dt) -> Optional[str]:
    """将 datetime 转换为 ISO 8601 字符串，None-safe"""
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return None


def _event_to_dict(event: EventLog) -> dict:
    """将 EventLog ORM 对象转为可序列化字典"""
    payload = {}
    if event.payload:
        try:
            payload = json.loads(event.payload)
        except (json.JSONDecodeError, TypeError):
            payload = str(event.payload)

    state_snapshot = None
    if event.state_snapshot:
        try:
            state_snapshot = json.loads(event.state_snapshot)
        except (json.JSONDecodeError, TypeError):
            state_snapshot = str(event.state_snapshot)

    handler_summary = None
    if event.handler_summary:
        try:
            handler_summary = json.loads(event.handler_summary)
        except (json.JSONDecodeError, TypeError):
            handler_summary = str(event.handler_summary)

    return {
        "id": event.id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "payload": payload,
        "plan_id": event.plan_id,
        "saga_id": event.saga_id,
        "state_snapshot": state_snapshot,
        "handler_summary": handler_summary,
        "status": event.status,
        "created_at": _safe_iso(event.created_at),
    }


# ════════════════════════════════════════════════════════
# GET /api/events — 事件列表（分页 + 过滤）
# ════════════════════════════════════════════════════════


@router.get("")
def list_events(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    event_type: Optional[str] = Query(None, description="按事件类型过滤"),
    plan_id: Optional[str] = Query(None, description="按 ProductPlan ID 过滤"),
    saga_id: Optional[str] = Query(None, description="按 Saga 事务 ID 过滤"),
    status: Optional[str] = Query(None, description="按状态过滤 (emitted/processed/partial_failed/failed)"),
    current_user: User = Depends(require_role("admin", "quality_engineer")),
    db: Session = Depends(get_db),
) -> dict:
    """获取事件日志列表，支持分页和多维度过滤

    按 created_at 降序排列（最新事件在前）。
    返回 {items, total, page, page_size} 格式。
    """
    try:
        query = db.query(EventLog)

        if event_type:
            query = query.filter(EventLog.event_type == event_type)
        if plan_id:
            query = query.filter(EventLog.plan_id == plan_id)
        if saga_id:
            query = query.filter(EventLog.saga_id == saga_id)
        if status:
            query = query.filter(EventLog.status == status)

        total = query.count()
        items = (
            query
            .order_by(desc(EventLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [_event_to_dict(e) for e in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.exception("获取事件列表失败")
        raise HTTPException(status_code=500, detail=f"获取事件列表失败: {str(e)}")


# ════════════════════════════════════════════════════════
# GET /api/events/types — 已注册事件类型列表
# ════════════════════════════════════════════════════════


@router.get("/types")
def list_event_types(
    current_user: User = Depends(require_role("admin", "quality_engineer")),
    db: Session = Depends(get_db),
) -> dict:
    """获取已注册事件类型列表（去重）

    返回 {types: [...]} 格式，按 event_type 字母序排列。
    """
    try:
        rows = (
            db.query(EventLog.event_type)
            .distinct()
            .order_by(EventLog.event_type)
            .all()
        )
        types = [r[0] for r in rows if r[0]]
        return {"types": types, "total": len(types)}
    except Exception as e:
        logger.exception("获取事件类型列表失败")
        raise HTTPException(status_code=500, detail=f"获取事件类型列表失败: {str(e)}")


# ════════════════════════════════════════════════════════
# GET /api/events/{id} — 事件详情
# ════════════════════════════════════════════════════════


@router.get("/{event_id}")
def get_event(
    event_id: int,
    current_user: User = Depends(require_role("admin", "quality_engineer")),
    db: Session = Depends(get_db),
) -> dict:
    """获取指定事件的详细信息"""
    try:
        event = db.query(EventLog).filter(EventLog.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail=f"事件 #{event_id} 不存在")
        return _event_to_dict(event)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("获取事件详情失败: event_id=%s", event_id)
        raise HTTPException(status_code=500, detail=f"获取事件详情失败: {str(e)}")
