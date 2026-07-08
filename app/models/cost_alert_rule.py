"""成本超标预警引擎 — 数据模型

2张核心表：
  cost_alert_rules  → 预警规则配置
  alert_events      → 超标事件记录
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CostAlertRule(Base):
    """成本超标预警规则"""
    __tablename__ = "cost_alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    threshold_pct = Column(Float, default=0, comment="超标百分比阈值（如 10 表示超过预算10%）")
    threshold_amount = Column(Float, default=0, comment="超标金额阈值（元）")
    project_type = Column(String(50), nullable=True, comment="适用产品类型（为空则全部）")
    enabled = Column(Boolean, default=True, comment="是否启用")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    events = relationship("AlertEvent", back_populates="rule", cascade="all, delete-orphan")


class AlertEvent(Base):
    """超标事件 — 超标规则触发后生成的记录"""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("cost_alert_rules.id"), nullable=False, comment="关联规则ID")
    rule_name = Column(String(100), nullable=False, comment="规则名称快照")

    # 核算单关联
    sheet_id = Column(Integer, ForeignKey("cost_accounting_sheets.id"), nullable=False, comment="关联核算单ID")
    product_plan_id = Column(String(36), nullable=False, comment="关联策划ID (UUID)")
    plan_name = Column(String(200), nullable=True, comment="策划名称快照")

    # 超标指标
    target_amount = Column(Float, default=0, comment="目标成本")
    actual_amount = Column(Float, default=0, comment="实际成本")
    variance_amount = Column(Float, default=0, comment="差异额=实际-目标")
    variance_pct = Column(Float, default=0, comment="差异率%")
    threshold_pct = Column(Float, default=0, comment="阈值百分比快照")
    threshold_amount = Column(Float, default=0, comment="阈值金额快照")

    # 等级与消息
    alert_level = Column(String(20), default="warning", comment="预警等级: warning/critical")
    message = Column(Text, nullable=True, comment="预警描述")

    # 处理状态
    is_read = Column(Boolean, default=False, comment="是否已读")
    is_resolved = Column(Boolean, default=False, comment="是否已处理")
    resolved_at = Column(DateTime, nullable=True, comment="处理时间")

    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="创建时间")

    # 关联
    rule = relationship("CostAlertRule", foreign_keys=[rule_id], back_populates="events")
