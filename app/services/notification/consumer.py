"""事件驱动推送引擎 — 事件消费者

工作流:
1. 监听事件总线上的业务事件
2. 确定对应的通知事件类型
3. 查询目标用户的通知偏好 → 匹配可用渠道
4. 渲染消息模板
5. 调用 unified send() 推送
6. 记录推送日志到 notification_logs 表
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.events import bus, EventTypes
from app.services.notification.events import NotificationEventType
from app.services.notification import send as notification_send
from app.models.notification_channel import NotificationChannel

logger = logging.getLogger(__name__)

# ── 事件映射: 业务事件类型 → 通知事件类型 ──
_EVENT_MAP: dict[str, NotificationEventType] = {
    EventTypes.PLAN_APPROVED: NotificationEventType.APPROVAL_RESULT,
    EventTypes.APPROVAL_COMPLETED: NotificationEventType.APPROVAL_RESULT,
    EventTypes.APPROVAL_REJECTED: NotificationEventType.APPROVAL_RESULT,
}

# ── 消息模板（简单 str.format 模板，未来可替换为 Jinja2） ──
_TEMPLATES: dict[NotificationEventType, str] = {
    NotificationEventType.APPROVAL_PENDING: (
        "📋 审批待处理\n"
        "项目: {plan_name}\n"
        "发起人: {requester}\n"
        "请尽快处理审批。"
    ),
    NotificationEventType.APPROVAL_RESULT: (
        "✅ 审批完成\n"
        "项目: {plan_name}\n"
        "状态: {status}\n"
        "处理人: {username}"
    ),
    NotificationEventType.PLAN_ADVANCED: (
        "📌 策划阶段推进\n"
        "项目: {plan_name}\n"
        "阶段: {stage}\n"
        "操作人: {username}"
    ),
    NotificationEventType.COST_ALERT: (
        "⚠️ 成本预警\n"
        "项目: {plan_name}\n"
        "详情: {detail}"
    ),
}

# ── 日志记录 ──


def _log_notification(
    db: Session,
    *,
    request_id: Optional[str],
    channel: str,
    event_type: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    """记录通知推送日志到 notification_logs 表"""
    try:
        from app.models.notification_log import NotificationLog

        log = NotificationLog(
            request_id=request_id,
            channel=channel,
            event_type=event_type,
            status=status,
            error=error,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.exception("unexpected error")
        db.rollback()
        logger.error("通知日志记录失败: %s", e)


# ── 查询用户通知偏好 ──


def _get_user_channels(db: Session, username: str) -> list[dict]:
    """查询用户可用的通知通道

    当前实现: 返回所有已启用的全局通知通道。
    未来可扩展为按用户偏好过滤（user_notification_prefs 表，支持
    event_type + channel_type 粒度控制）。
    """
    channels = (
        db.query(NotificationChannel)
        .filter(NotificationChannel.enabled == True)
        .all()
    )
    return [
        {
            "channel_type": ch.channel_type,
            "webhook_url": ch.webhook_url,
            "secret": ch.secret or "",
            "daily_limit": ch.daily_limit,
            "channel_id": ch.id,
        }
        for ch in channels
    ]


# ── 消息渲染 ──


def _render_message(event_type: NotificationEventType, **kwargs) -> str:
    """根据事件类型和上下文渲染消息内容"""
    template = _TEMPLATES.get(event_type)
    if template is None:
        return f"[{event_type.value}] {json.dumps(kwargs, ensure_ascii=False)}"
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning("消息模板渲染缺少参数: %s (kwargs=%s)", e, kwargs)
        return f"[{event_type.value}] {json.dumps(kwargs, ensure_ascii=False)}"


# ── 事件类型推断 ──


def _determine_notification_event(biz_event_type: str) -> Optional[NotificationEventType]:
    """根据业务事件类型推断对应的通知事件类型"""
    # 直接映射
    mapped = _EVENT_MAP.get(biz_event_type)
    if mapped:
        return mapped

    # 按前缀匹配
    if biz_event_type.startswith("approval.pending"):
        return NotificationEventType.APPROVAL_PENDING
    if biz_event_type.startswith("plan.approved"):
        return NotificationEventType.APPROVAL_RESULT
    if biz_event_type.startswith("approval.result"):
        return NotificationEventType.APPROVAL_RESULT
    if biz_event_type.startswith("plan.advanced") or (
        biz_event_type.startswith("plan.") and "advanced" in biz_event_type
    ):
        return NotificationEventType.PLAN_ADVANCED
    if biz_event_type.startswith("cost.") or biz_event_type.startswith("alert.cost"):
        return NotificationEventType.COST_ALERT

    return None


def _get_target_username(**kwargs) -> Optional[str]:
    """从事件上下文中提取目标用户名"""
    for key in ("username", "created_by", "requester", "assignee", "user"):
        val = kwargs.get(key)
        if val and isinstance(val, str):
            return val
    return None


# ── 主处理逻辑 ──


def on_notification_event(biz_event_type: str, **kwargs) -> None:
    """通知事件处理器 — 供 EventBus 注册

    处理流程:
    1. 确定通知事件类型
    2. 获取目标用户
    3. 查询用户可用渠道
    4. 渲染消息内容
    5. 逐渠道推送
    6. 记录推送日志
    """
    # Step 1: 确定通知事件类型
    notif_type = _determine_notification_event(biz_event_type)
    if notif_type is None:
        logger.debug("业务事件 '%s' 无对应通知类型，跳过", biz_event_type)
        return

    # Step 2: 提取目标用户
    username = _get_target_username(**kwargs)
    if not username:
        logger.warning("无法从事件上下文提取目标用户: %s", kwargs)
        return

    # Step 3: 渲染消息
    content = _render_message(notif_type, **kwargs)

    # Step 4: 查询渠道 + 推送 + 记录
    db = SessionLocal()
    try:
        channels = _get_user_channels(db, username)
        if not channels:
            logger.info("用户 '%s' 无可用通知通道，跳过推送", username)
            return

        for ch in channels:
            result = notification_send(
                channel_type=ch["channel_type"],
                content=content,
                webhook_url=ch["webhook_url"],
                secret=ch["secret"],
                daily_limit=ch["daily_limit"],
                channel_id=ch["channel_id"],
            )

            status = "sent" if result.get("ok") else "failed"
            error = result.get("msg") if not result.get("ok") else None

            _log_notification(
                db,
                request_id=kwargs.get("plan_id"),
                channel=ch["channel_type"],
                event_type=notif_type.value,
                status=status,
                error=error,
            )

            if result.get("ok"):
                logger.info(
                    "通知推送成功: event=%s, user=%s, channel=%s",
                    notif_type.value, username, ch["channel_type"],
                )
            else:
                logger.warning(
                    "通知推送失败: event=%s, user=%s, channel=%s, error=%s",
                    notif_type.value, username, ch["channel_type"], error,
                )

    except Exception as e:
        logger.error("通知处理器异常: %s", e, exc_info=True)
    finally:
        db.close()


# ── 注册到 EventBus ──


def register_handlers() -> None:
    """注册通知事件处理器到 EventBus"""
    # plan.approved → 通知审批结果
    bus.on(EventTypes.PLAN_APPROVED, on_notification_event)
    # approval.pending → 通知待审批
    bus.on("approval.pending", on_notification_event)

    logger.info("通知事件处理器已注册 (%d 个事件)", 2)


__all__ = ["on_notification_event", "register_handlers"]
