"""ROS Event Bus — Planning Capability 事件发布器

遵循 D2-2 Event Metadata Standard Header 格式。
当前为同步日志模式（后续替换为异步消息队列）。
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def emit(
    event_type: str,
    payload: dict,
    *,
    version: int = 1,
    source: str = "planning",
    producer: str = "planning.service",
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    tenant_id: str = "default",
    user_id: Optional[str] = None,
) -> str:
    """发布事件 — 遵循 D2-2 Event Metadata Standard。

    当前实现：同步日志模式。
    后续实现：Event Bus 异步发布 + 持久化到 Event Store。

    Returns:
        event_id: 发布成功的事件 ID

    Raises:
        SchemaValidationError: 如果 Schema 验证开启且失败
    """
    event_id = _uuid()
    event = {
        "metadata": {
            "identity": {
                "event_id": event_id,
                "event_type": event_type,
                "version": version,
            },
            "context": {
                "timestamp": _now_iso(),
                "source": source,
                "producer": producer,
                "correlation_id": correlation_id or _uuid(),
                "causation_id": causation_id,
                "trace_id": trace_id or _uuid().replace("-", ""),
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        },
        "payload": payload,
    }

    # 当前：日志输出（后续替换为 Event Bus 发布）
    logger.info(
        "EVENT: %s | %s | %s",
        event_type,
        event_id,
        json.dumps(payload, ensure_ascii=False, default=str),
    )

    # TODO: Phase 4 实现
    # - Event Store 持久化
    # - Event Bus 异步发布
    # - Schema Validation (D2-4)
    # - DLQ on failure (D2-4)

    return event_id
