"""Webhook 订阅模型 — 单一事件类型订阅配置"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Index
from app.core.database import Base


class WebhookSubscription(Base):
    """Webhook 订阅 — 配置外部 URL 接收 ROS 事件回调

    与 webhook.py 中的 WebhookSubscription 不同，本模型使用
    单一 event_type 字段而非 JSON 数组，适用于简单订阅场景。
    """

    __tablename__ = "webhook_subscriptions_v2"

    __table_args__ = (
        Index('ix_sub_enabled_event_type', 'enabled', 'event_type'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="订阅名称")
    url = Column(String(500), nullable=False, comment="目标回调URL")
    event_type = Column(String(100), nullable=False, index=True, comment="订阅的事件类型，如 'plan.approved'")
    secret = Column(String(255), nullable=True, comment="HMAC-SHA256 签名密钥")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(String(100), nullable=True, comment="创建者用户名/ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
