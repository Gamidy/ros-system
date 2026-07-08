"""EventGraph API — Digital Thread 事件图查询

提供 ECR/ECO 的完整事件链和因果链查询。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_menu
from app.core.security import get_current_user
from app.models.user import User
from app.services.event_store_service import EventStoreService

router = APIRouter(prefix="/v2/event-graph", tags=["EventGraph"])

VALID_AGGREGATE_TYPES = {"ecr", "eco"}


def _event_to_dict(e) -> dict:
    """将 EventStore ORM 转为 dict"""
    return {
        "id": e.id,
        "event_type": e.event_type,
        "aggregate_type": e.aggregate_type,
        "aggregate_id": e.aggregate_id,
        "correlation_id": e.correlation_id,
        "causation_id": e.causation_id,
        "event_data": e.event_data,
        "producer": e.producer,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/{aggregate_type}/{aggregate_id}")
def get_event_chain(
    aggregate_type: str,
    aggregate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> list[dict]:
    """获取某个聚合 (ECR/ECO) 的完整事件链"""
    if aggregate_type not in VALID_AGGREGATE_TYPES:
        raise HTTPException(status_code=400, detail="aggregate_type 必须是 ecr 或 eco")
    events = EventStoreService.get_event_chain(db, aggregate_type, aggregate_id)
    return [_event_to_dict(e) for e in events]


@router.get("/{aggregate_type}/{aggregate_id}/causation")
def get_causation_chain(
    aggregate_type: str,
    aggregate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> list[dict]:
    """从最新事件出发沿 causation_id 回溯因果链"""
    if aggregate_type not in VALID_AGGREGATE_TYPES:
        raise HTTPException(status_code=400, detail="aggregate_type 必须是 ecr 或 eco")
    events = EventStoreService.get_event_chain(db, aggregate_type, aggregate_id)
    if not events:
        return []
    last_event = events[-1]
    chain = EventStoreService.get_causation_chain(db, last_event.id)
    return [_event_to_dict(e) for e in chain]
