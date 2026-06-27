"""WebSocket 事件桥接 — 将 EventBus 事件推送到 WebSocket 客户端

注册入口: register_handlers() 在 event_handlers.py 启动时调用

工作流:
  1. 监听 EventBus 上的业务事件
  2. 查找目标用户
  3. 构造 WS 消息（含 action 路由字段）并通过 ws_manager 推送
"""
import json
import logging
from datetime import datetime, timezone

from app.services.events import bus, EventTypes
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)


# ── action 路由映射 ─────────────────────────────────
# 通知类型 → 前端路由目标
_NOTIFICATION_ACTIONS: dict[str, str] = {
    "approval": "/approvals",
    "notification": "/product-plans/{id}",
    "review": "/product-plans/{plan_id}?tab=review",
}


def _resolve_action(msg_type: str, payload: dict) -> str:
    """根据消息类型和 payload 解析前端路由 action

    Args:
        msg_type: 消息类型 (approval / notification / review)
        payload:  消息载荷，可包含 id / plan_id 等

    Returns:
        前端路由路径字符串
    """
    base = _NOTIFICATION_ACTIONS.get(msg_type, "")
    if not base:
        return "/notifications"

    plan_id = payload.get("plan_id") or payload.get("request_id")
    if plan_id is not None:
        return base.replace("{id}", str(plan_id)).replace("{plan_id}", str(plan_id))
    return base.rstrip("/")


async def _push_ws(
    event_type: str,
    msg_type: str,
    payload: dict,
    target_username: str,
    *,
    action: str = "",
) -> None:
    """向指定用户的 WebSocket 推送消息（含 action 路由）"""
    if not action:
        action = _resolve_action(msg_type, payload)

    message = {
        "type": msg_type,
        "action": action,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    sent = await ws_manager.send_to_user(target_username, message)
    if sent > 0:
        logger.debug(
            "WS 推送成功: event=%s, user=%s, action=%s, sent=%d",
            event_type, target_username, action, sent,
        )


def _on_approval_event(event_type: str, **kwargs):
    """审批事件处理器 — 推送审批通知给申请人 (requester)

    从 event_handlers.py 的 bus.on() 同步调用。
    兼容两种场景：
    - 有运行事件循环（FastAPI请求上下文）→ loop.create_task()
    - 无事件循环（后台线程/Celery）→ asyncio.run()
    """
    import asyncio

    requester = kwargs.get("requester")
    if not requester:
        logger.debug("审批事件缺少 requester: event=%s", event_type)
        return

    title = kwargs.get("title", "")
    comment = kwargs.get("comment", "")
    approval_status = "approved" if event_type == EventTypes.APPROVAL_COMPLETED else "rejected"

    payload = {
        "request_id": kwargs.get("request_id", 0),
        "title": title,
        "status": approval_status,
        "request_type": kwargs.get("request_type", ""),
        "comment": comment,
        "content": f"审批「{title}」状态已更新为: {approval_status}",
    }

    # ── 同步发送邮件通知（离线提醒）──
    try:
        from app.services.email_notifier import send_approval_email
        send_approval_email(
            requester=requester,
            title=title,
            status=approval_status,
            request_id=kwargs.get("request_id", 0),
            comment=comment,
        )
    except Exception as e:
        logger.error("邮件通知发送异常: %s", e, exc_info=True)

    # 检测是否已有运行中的事件循环
    try:
        loop = asyncio.get_running_loop()
        # 已在事件循环中 → create_task 安全
        loop.create_task(
            _push_ws(
                event_type,
                "approval",
                payload,
                requester,
                action="/approvals",
            )
        )
    except RuntimeError:
        # 无运行事件循环 → asyncio.run()
        try:
            asyncio.run(
                _push_ws(
                    event_type,
                    "approval",
                    payload,
                    requester,
                    action="/approvals",
                )
            )
        except RuntimeError as exc:
            logger.warning("WS 推送失败（无可用事件循环）: %s", exc)


def _on_plan_event(event_type: str, **kwargs):
    """策划事件处理器 — 推送策划阶段更新通知

    监听 plan.* 事件，推送通知给相关用户。
    """
    import asyncio

    username = kwargs.get("username") or kwargs.get("created_by")
    if not username:
        logger.debug("策划事件缺少目标用户: event=%s", event_type)
        return

    plan_id = kwargs.get("plan_id", "")
    plan_name = kwargs.get("plan_name", "")
    new_stage = kwargs.get("new_stage", "")

    payload = {
        "plan_id": str(plan_id) if plan_id else "",
        "plan_name": plan_name,
        "stage": new_stage or "",
    }

    action = f"/product-plans/{plan_id}" if plan_id else "/product-plans"

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            _push_ws(event_type, "notification", payload, username, action=action)
        )
    except RuntimeError:
        try:
            asyncio.run(
                _push_ws(event_type, "notification", payload, username, action=action)
            )
        except RuntimeError as exc:
            logger.warning("WS 推送失败（无可用事件循环）: %s", exc)


def _on_review_event(event_type: str, **kwargs):
    """评审事件处理器 — 推送评审通知

    监听 review.* 事件，推送通知给相关用户。
    路由目标: /product-plans/{plan_id}?tab=review
    """
    import asyncio

    username = kwargs.get("username") or kwargs.get("created_by") or kwargs.get("reviewer")
    if not username:
        logger.debug("评审事件缺少目标用户: event=%s", event_type)
        return

    plan_id = kwargs.get("plan_id", "")
    plan_name = kwargs.get("plan_name", "")

    payload = {
        "plan_id": str(plan_id) if plan_id else "",
        "plan_name": plan_name,
    }

    action = f"/product-plans/{plan_id}?tab=review" if plan_id else "/product-plans"

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            _push_ws(event_type, "review", payload, username, action=action)
        )
    except RuntimeError:
        try:
            asyncio.run(
                _push_ws(event_type, "review", payload, username, action=action)
            )
        except RuntimeError as exc:
            logger.warning("WS 推送失败（无可用事件循环）: %s", exc)


# ── 注册入口 ──────────────────────────────────────────


def register_handlers() -> None:
    """注册 WebSocket 事件处理器到 EventBus"""
    bus.on(EventTypes.APPROVAL_COMPLETED, _on_approval_event)
    bus.on(EventTypes.APPROVAL_REJECTED, _on_approval_event)

    # ── 策划阶段推送 ──
    for evt in [
        "plan.competitor_done",
        "plan.definition_done",
        "plan.costing_done",
        "plan.tech_input_done",
        "plan.project_init_done",
        "plan.released",
    ]:
        bus.on(evt, _on_plan_event)

    # ── 评审事件推送 ──
    bus.on("review.submitted", _on_review_event)
    bus.on("review.completed", _on_review_event)

    logger.info(
        "WebSocket 事件桥接已注册: approval/plan/review — 共 %d 个事件",
        len([e for e in bus.handlers if "approval" in e or "plan." in e or "review." in e]),
    )
