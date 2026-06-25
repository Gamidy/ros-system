"""通知事件类型枚举

映射业务事件到通知事件，用于事件驱动推送引擎。
"""
from enum import Enum


class NotificationEventType(str, Enum):
    """通知事件类型 — 对应业务场景"""
    APPROVAL_PENDING = "approval.pending"         # 审批待处理（通知审批人）
    APPROVAL_RESULT = "approval.result"           # 审批结果（通知发起人）
    PLAN_ADVANCED = "plan.advanced"               # 策划阶段推进
    COST_ALERT = "cost.alert"                     # 成本预警


__all__ = ["NotificationEventType"]
