"""EventStoreService — Digital Thread 事件存储服务

记录 ECR / ECO 的每个状态变更为可追溯事件链。
correlation_id 聚合同一流程, causation_id 形成因果链表。

依赖:
- models/event_store.EventStore  ORM 模型
- sqlalchemy.orm.Session
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.event_store import EventStore

logger = logging.getLogger(__name__)


class EventStoreService:
    """事件存储服务 — Digital Thread 核心

    记录 ECR/ECO 的每个状态变更为可追溯事件链。
    correlation_id 聚合同一流程, causation_id 形成因果链表。
    """

    @staticmethod
    def record(
        db: Session,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
        correlation_id: Optional[str] = None,
        causation_id: Optional[int] = None,
        event_data: Optional[dict] = None,
        producer: Optional[str] = None,
    ) -> EventStore:
        """记录一条事件

        - causation_id 未传时, 自动查询该 aggregate 最新事件的 id
        - correlation_id 未传时, 自动查询该 aggregate 最新事件的 correlation_id
        - producer 默认 f"{aggregate_type}.service"
        """
        try:
            # 推导 correlation_id: 未传时自动继承该 aggregate 上一个事件的
            if correlation_id is None:
                try:
                    last_event = (
                        db.query(EventStore)
                        .filter(
                            EventStore.aggregate_type == aggregate_type,
                            EventStore.aggregate_id == aggregate_id,
                        )
                        .order_by(EventStore.id.desc())
                        .first()
                    )
                    if last_event is not None:
                        correlation_id = last_event.correlation_id
                except Exception as e:
                    logger.warning(
                        "EventStoreService.record: 查询上一个 correlation_id 失败: %s", e
                    )

            # 仍未确定则生成新 UUID
            if correlation_id is None:
                correlation_id = str(uuid.uuid4())

            # 推导 causation_id: 未传时自动指向该 aggregate 最新事件的 id
            if causation_id is None:
                try:
                    last_event = (
                        db.query(EventStore)
                        .filter(
                            EventStore.aggregate_type == aggregate_type,
                            EventStore.aggregate_id == aggregate_id,
                        )
                        .order_by(EventStore.id.desc())
                        .first()
                    )
                    if last_event is not None:
                        causation_id = last_event.id
                except Exception as e:
                    logger.warning(
                        "EventStoreService.record: 查询上一个 causation_id 失败: %s", e
                    )

            # producer 默认值
            if producer is None:
                producer = f"{aggregate_type}.service"

            # 序列化 event_data
            import json

            event_data_json: Optional[str] = None
            if event_data is not None:
                try:
                    event_data_json = json.dumps(
                        event_data, ensure_ascii=False, default=str
                    )
                except Exception as e:
                    logger.warning(
                        "EventStoreService.record: event_data 序列化失败: %s", e
                    )

            event = EventStore(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                correlation_id=correlation_id,
                causation_id=causation_id,
                event_data=event_data_json,
                producer=producer,
                created_at=datetime.now(timezone.utc),
            )
            db.add(event)
            db.flush()
            return event

        except Exception as e:
            logger.exception(
                "EventStoreService.record 失败: type=%s agg=%s#%s",
                event_type,
                aggregate_type,
                aggregate_id,
            )
            raise

    @staticmethod
    def get_event_chain(
        db: Session, aggregate_type: str, aggregate_id: int
    ) -> list[EventStore]:
        """获取某个聚合的所有事件 (按 created_at 正序)"""
        try:
            return (
                db.query(EventStore)
                .filter(
                    EventStore.aggregate_type == aggregate_type,
                    EventStore.aggregate_id == aggregate_id,
                )
                .order_by(EventStore.created_at.asc())
                .all()
            )
        except Exception as e:
            logger.exception(
                "EventStoreService.get_event_chain 失败: agg=%s#%s",
                aggregate_type,
                aggregate_id,
            )
            return []

    @staticmethod
    def get_causation_chain(db: Session, event_id: int) -> list[EventStore]:
        """从指定事件出发, 沿 causation_id 回溯整条因果链"""
        chain: list[EventStore] = []
        try:
            current_id: Optional[int] = event_id
            visited: set[int] = set()
            while current_id is not None:
                if current_id in visited:
                    logger.warning(
                        "EventStoreService.get_causation_chain: 检测到循环引用, 中断于 id=%s",
                        current_id,
                    )
                    break
                visited.add(current_id)

                event = (
                    db.query(EventStore)
                    .filter(EventStore.id == current_id)
                    .first()
                )
                if event is None:
                    break
                chain.append(event)
                current_id = event.causation_id

            # 按时间正序返回 (从最早的祖先到目标事件)
            chain.reverse()
            return chain
        except Exception as e:
            logger.exception(
                "EventStoreService.get_causation_chain 失败: event_id=%s",
                event_id,
            )
            return []

    @staticmethod
    def get_correlation_graph(
        db: Session, correlation_id: str
    ) -> list[EventStore]:
        """获取同一 correlation_id 的所有事件 (完整流程)"""
        try:
            return (
                db.query(EventStore)
                .filter(EventStore.correlation_id == correlation_id)
                .order_by(EventStore.created_at.asc())
                .all()
            )
        except Exception as e:
            logger.exception(
                "EventStoreService.get_correlation_graph 失败: correlation_id=%s",
                correlation_id,
            )
            return []
