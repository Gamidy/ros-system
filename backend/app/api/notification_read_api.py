"""已读/未读跨渠道同步 API

Endpoints:
- POST /api/user/notification-read — 标记通知已读（跨渠道同步 + WebSocket推送角标更新）
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification_read import NotificationReadStatus, CHANNEL_TYPES
from app.models.alert import Notification
from app.services.ws_manager import ws_manager
from app.schemas.notification_read import (
    NotificationReadRequest,
    NotificationReadOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["通知已读/未读跨渠道同步"])


# ── 内部辅助: WebSocket 推送已读状态更新 ──


def _push_read_update_sync(username: str, notification_id: str, read_at: str) -> None:
    """同步上下文中触发 WebSocket 推送（非阻塞）

    向用户推送通知已读状态变更事件，前端可据此更新角标和列表。
    """
    message = {
        "type": "notification_read",
        "action": "read",
        "payload": {
            "notification_id": notification_id,
            "read_at": read_at,
        },
    }

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(ws_manager.send_to_user(username, message))
            return
    except RuntimeError:
        pass

    # 无运行中事件循环 → 临时创建
    try:
        asyncio.run(ws_manager.send_to_user(username, message))
    except RuntimeError as exc:
        logger.warning("WS推送已读状态失败（无可用事件循环）: %s", exc)


# ════════════════════════════════════════════════════════════
# POST — 标记通知已读（跨渠道同步）
# ════════════════════════════════════════════════════════════


@router.post("/notification-read", response_model=NotificationReadOut)
def mark_notification_read(
    body: NotificationReadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationReadOut:
    """标记通知已读，并同步标记所有渠道为已读

    跨渠道同步策略：
    1. 在当前渠道上创建/更新已读记录
    2. 在所有其他渠道上也创建已读记录（使用相同的时间戳）
    3. 通过 WebSocket 向用户推送已读状态更新，以便前端更新角标
    4. 返回已同步的渠道列表

    前端调用方式：
        POST /api/user/notification-read
        { "notification_id": "123", "channel_type": "websocket" }
    """
    now = datetime.now(timezone.utc)
    user_id = str(current_user.username)
    synced: list[str] = []

    # 先验证 channel_type 是否有效
    if body.channel_type not in CHANNEL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的渠道类型: {body.channel_type}，可选: {CHANNEL_TYPES}",
        )

    for channel_type in CHANNEL_TYPES:
        try:
            # 查找是否已有记录
            existing = (
                db.query(NotificationReadStatus)
                .filter(
                    NotificationReadStatus.notification_id == body.notification_id,
                    NotificationReadStatus.user_id == user_id,
                    NotificationReadStatus.channel_type == channel_type,
                )
                .first()
            )

            if existing:
                # 已有记录则更新 read_at
                existing.read_at = now
            else:
                # 无记录则创建
                status = NotificationReadStatus(
                    notification_id=body.notification_id,
                    user_id=user_id,
                    channel_type=channel_type,
                    read_at=now,
                )
                db.add(status)

            synced.append(channel_type)
        except Exception as e:
            logger.error(
                "标记已读失败: notification_id=%s, channel=%s, error=%s",
                body.notification_id, channel_type, e,
            )
            raise HTTPException(
                status_code=500,
                detail=f"标记已读失败(channel={channel_type}): {str(e)}",
            )

    # 如果通知在 notifications 表中存在，同步更新 is_read 标记
    try:
        notif = (
            db.query(Notification)
            .filter(Notification.id == int(body.notification_id))
            .first()
        )
        if notif and not notif.is_read:
            notif.is_read = True
            notif.read_at = now
    except (ValueError, Exception) as e:
        # notification_id 可能不是纯数字，或通知不存在，忽略
        logger.debug(
            "同步更新 Notification.is_read 跳过: notification_id=%s, error=%s",
            body.notification_id, e,
        )

    db.commit()

    logger.info(
        "通知已读标记完成: notification_id=%s, user=%s, synced_channels=%s",
        body.notification_id, user_id, synced,
    )

    # WebSocket 推送 — 更新角标
    _push_read_update_sync(user_id, body.notification_id, now.isoformat())

    return NotificationReadOut(
        ok=True,
        notification_id=body.notification_id,
        user_id=user_id,
        synced_channels=synced,
        read_at=now,
    )
