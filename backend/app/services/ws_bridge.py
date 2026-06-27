"""WebSocket 事件桥接 — 将 EventBus 事件推送到 WebSocket 客户端

注册入口: register_handlers() 在 event_handlers.py 启动时调用

工作流:
  1. 监听 EventBus 上的业务事件
  2. 查找目标用户
  3. 构造 WS 消息并通过 ws_manager 推送
"""
import json
import logging
from datetime import datetime, timezone

from app.services.events import bus, EventTypes
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)


# ── 审批事件处理 ──────────────────────────────────────


async def _push_ws(event_type: str, msg_type: str, payload: dict, target_username: str) -> None:
    """向指定用户的 WebSocket 推送消息"""
    message = {
        "type": msg_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    sent = await ws_manager.send_to_user(target_username, message)
    if sent > 0:
        logger.debug(
            "WS 推送成功: event=%s, user=%s, sent=%d",
            event_type, target_username, sent,
        )


def _on_approval_event(event_type: str, **kwargs):
    """审批事件处理器 — 推送审批通知给申请人 (requester)

    从 event_handlers.py 的 bus.on() 同步调用。
    由于 ws_manager.send_to_user 是 async 的，这里用 asyncio.run 执行。
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
        "request_id": kwargs.get("request_id"),
        "title": title,
        "status": approval_status,
        "request_type": kwargs.get("request_type", ""),
        "comment": comment,
        "content": f"审批「{title}」状态已更新为: {approval_status}",
    }

    try:
        asyncio.run(_push_ws(event_type, "approval", payload, requester))
    except RuntimeError:
        # 如果已在事件循环中，用 run_coroutine_threadsafe
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_push_ws(event_type, "approval", payload, requester))
                return
        except RuntimeError:
            pass
        logger.warning("WS 推送失败（无事件循环）: event=%s, user=%s", event_type, requester)


# ── 注册入口 ──────────────────────────────────────────


def register_handlers() -> None:
    """注册 WebSocket 事件处理器到 EventBus"""
    bus.on(EventTypes.APPROVAL_COMPLETED, _on_approval_event)
    bus.on(EventTypes.APPROVAL_REJECTED, _on_approval_event)

    logger.info("WebSocket 事件桥接已注册 (approval.completed / approval.rejected)")
