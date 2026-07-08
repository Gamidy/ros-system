"""Webhook 订阅与投递日志模型"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, func
from app.core.database import Base


class WebhookSubscription(Base):
    """Webhook 订阅 — 配置外部 URL 接收 ROS 事件回调"""

    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    name = Column(String(100), nullable=False, comment="订阅名称")
    url = Column(String(500), nullable=False, comment="回调URL")
    events = Column(JSON, nullable=False, comment="订阅的事件类型列表，如 [\"plan.approved\", \"test.done_with_ng\"]")
    secret = Column(String(128), nullable=True, comment="HMAC-SHA256 签名密钥")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_triggered_at = Column(DateTime, nullable=True, comment="最近一次触发时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class WebhookDeliveryLog(Base):
    """Webhook 投递日志 — 每次推送尝试的记录"""

    __tablename__ = "webhook_delivery_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id"), nullable=False, index=True, comment="关联订阅ID")
    event_type = Column(String(100), nullable=False, comment="事件类型")
    payload = Column(Text, nullable=True, comment="请求体JSON字符串")
    response_status = Column(Integer, nullable=True, comment="HTTP响应状态码")
    response_body = Column(Text, nullable=True, comment="HTTP响应体（截取前500字）")
    success = Column(Boolean, default=False, comment="是否推送成功")
    attempted_at = Column(DateTime, nullable=True, comment="本次推送时间")
    retry_count = Column(Integer, default=0, comment="已重试次数")
