"""消息推送通道模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from app.core.database import Base


class NotificationChannel(Base):
    """消息推送通道配置"""
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_type = Column(String(32), nullable=False, index=True, comment="通道类型: wecom / dingtalk")
    name = Column(String(128), nullable=False, comment="通道名称/备注")
    webhook_url = Column(String(512), nullable=False, comment="Webhook 机器人地址")
    secret = Column(String(256), nullable=True, default="", comment="签名密钥（钉钉必填，企微可选）")
    daily_limit = Column(Integer, nullable=False, default=1000, comment="每日消息条数上限")
    status = Column(String(16), nullable=False, default="active", comment="运行状态: active / rate_limited / error")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationChannel(id={self.id}, type={self.channel_type}, name={self.name}, enabled={self.enabled})>"
