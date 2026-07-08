"""WebSocket 端点 — 实时推送通知

端点:  GET /ws?token=xxx
协议:  JSON 文本帧
认证:  JWT token 作为查询参数

服务端 -> 客户端消息格式:
  {
    "type": "approval"|"alert"|"notification"|"system",
    "action": "/approvals"|"/product-plans/{id}"|"",
    "payload": {...},
    "timestamp": "..."
  }

客户端 -> 服务端:
  {"type": "ping"} — 心跳保活
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# ── action 路由映射 ─────────────────────────────────
_NOTIFICATION_ACTIONS: dict[str, str] = {
    "approval": "/approvals",
    "notification": "/product-plans/{id}",
    "review": "/product-plans/{plan_id}?tab=review",
}


def _resolve_action(msg_type: str, payload: dict) -> str:
    """根据消息类型和 payload 解析前端路由 action"""
    base = _NOTIFICATION_ACTIONS.get(msg_type, "")
    if not base:
        return "/notifications"

    plan_id = payload.get("plan_id") or payload.get("request_id")
    if plan_id is not None:
        return base.replace("{id}", str(plan_id)).replace("{plan_id}", str(plan_id))
    return base.rstrip("/")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 主端点

    流程:
      1. 认证 — 从 query param 解析 JWT token → 查 DB 获取 username
      2. 注册连接
      3. 循环接收消息（处理 ping/pong 心跳）
      4. 断开时清理
    """
    # ── Step 1: 认证 ──
    username = await ws_manager.authenticate(websocket)
    if username is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # ── Step 2: 注册连接 ──
    await ws_manager.connect(websocket, username)

    try:
        # ── Step 3: 消息循环 ──
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("WebSocket 收到非 JSON 消息: user=%s", username)
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                try:
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "payload": {},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }))
                except Exception:
                    logger.exception(f"unexpected: {e}")
                    break
            else:
                logger.debug(
                    "WebSocket 未知消息: user=%s, type=%s",
                    username, msg_type,
                )

    except WebSocketDisconnect:
        logger.info("WebSocket 正常断开: user=%s", username)
    except Exception as e:
        logger.warning("WebSocket 异常: user=%s, error=%s", username, e)
    finally:
        # ── Step 4: 清理 ──
        ws_manager.disconnect(websocket, username)


# ── 便捷推送函数（供其他模块调用） ──


async def push_to_user(
    username: str,
    msg_type: str,
    payload: dict,
    *,
    action: str = "",
) -> int:
    """向指定用户推送 WebSocket 消息

    Args:
        username: 目标用户名
        msg_type: 消息类型 (approval/alert/notification/system/review)
        payload:  消息载荷
        action:   前端路由路径（可选，自动推断）

    Returns:
        成功推送的连接数
    """
    if not action:
        action = _resolve_action(msg_type, payload)

    message = {
        "type": msg_type,
        "action": action,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return await ws_manager.send_to_user(username, message)


async def push_approval_notification(
    username: str,
    *,
    request_id: int,
    title: str,
    approval_status: str,
    request_type: str = "",
    comment: str = "",
) -> int:
    """推送审批通知给指定用户（含 /approvals 路由）"""
    return await push_to_user(
        username=username,
        msg_type="approval",
        payload={
            "request_id": request_id,
            "title": title,
            "status": approval_status,
            "request_type": request_type,
            "comment": comment,
            "content": f"审批「{title}」状态已更新为: {approval_status}",
        },
        action="/approvals",
    )
