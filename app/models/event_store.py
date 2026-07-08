"""EventStore — Digital Thread 事件溯源存储模型

记录 ECR / ECO 等聚合的每个状态变更，
支持 causation_id 因果链和 correlation_id 流程聚合。

字段设计:
- correlation_id: 聚合同一业务流程的多次事件
- causation_id: 因果指针，指向触发本事件的上一个事件
- event_data: 灵活的结构化 payload（JSON Text）
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.core.database import Base


class EventStore(Base):
    """Digital Thread 事件存储 — 可追溯事件链"""
    __tablename__ = "event_store"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True, comment="事件类型: ecr.submitted / eco.effective / ...")
    aggregate_type = Column(String(50), nullable=False, index=True, comment="聚合类型: ecr / eco / product_plan / ...")
    aggregate_id = Column(Integer, nullable=False, index=True, comment="聚合主键 ID")
    correlation_id = Column(String(36), nullable=False, index=True, comment="流程相关性 ID (UUID)")
    causation_id = Column(Integer, ForeignKey("event_store.id"), nullable=True, comment="因果指针 — 触发本事件的上一个事件 id")
    event_data = Column(Text, nullable=True, comment="事件载荷 JSON")
    producer = Column(String(100), nullable=False, comment="事件生产者: ecr.service / eco.service / ...")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True, comment="创建时间")

    def __repr__(self) -> str:
        return (
            f"<EventStore id={self.id} type={self.event_type!r} "
            f"agg={self.aggregate_type}#{self.aggregate_id} "
            f"corr={self.correlation_id}>"
        )
