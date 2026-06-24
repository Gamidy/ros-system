"""Event Log 事件存储模型

所有通过 EventBus 发射的事件自动记录到此表，
用于审计、回放、Debug 和未来 AI 分析。
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class EventLog(Base):
    """事件日志 — 持久化事件记录"""
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False, index=True, comment="事件类型")
    event_version = Column(String(10), default="v1", comment="事件版本")
    payload = Column(Text, nullable=True, comment="事件载荷JSON")
    handler_summary = Column(Text, nullable=True, comment="处理器执行摘要JSON: {handler_name: status}")
    status = Column(String(20), default="emitted", comment="emitted/processed/partial_failed/failed")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="创建时间")
