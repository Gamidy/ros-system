"""预警/通知/驾驶舱模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AlertRule(Base):
    """预警规则"""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    target_type = Column(String(50), nullable=False, comment="监控对象: project/certification/test/part/bom")
    rule_type = Column(String(50), nullable=False, comment="规则类型: overdue/threshold/status_change/risk")
    condition = Column(Text, nullable=False, comment="触发条件JSON")
    level = Column(Integer, default=2, comment="1紧急 2警告 3提示")
    is_enabled = Column(Boolean, default=True)
    notify_channels = Column(String(200), nullable=True, comment="通知渠道JSON: [\"feishu\",\"email\"]")
    notify_users = Column(String(300), nullable=True, comment="通知用户列表JSON")
    created_at = Column(DateTime, server_default=func.now())


class Alert(Base):
    """预警记录"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    level = Column(Integer, nullable=False, comment="1紧急 2警告 3提示")
    alert_type = Column(String(50), nullable=False, comment="overdue/threshold/status_change/risk/cdf_expiry")
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    rule = relationship("AlertRule")


class Notification(Base):
    """通知记录（钉钉/邮件等）"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    target_user = Column(String(100), nullable=False, comment="通知目标用户")
    channel = Column(String(20), default="feishu", comment="feishu/email/sms")
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_sent = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
