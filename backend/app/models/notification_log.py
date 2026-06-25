"""通知推送日志模型 — 记录每次推送的请求与结果"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class NotificationLog(Base):
    """通知推送日志"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), nullable=True, index=True, comment="关联业务 ID（如 plan_id）")
    channel = Column(String(32), nullable=False, comment="推送通道类型: wecom / dingtalk")
    event_type = Column(String(64), nullable=False, index=True, comment="通知事件类型")
    status = Column(String(20), nullable=False, default="sent", comment="推送状态: sent / failed")
    error = Column(Text, nullable=True, comment="错误信息（失败时填写）")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return (
            f"<NotificationLog(id={self.id}, event_type={self.event_type}, "
            f"channel={self.channel}, status={self.status})>"
        )
