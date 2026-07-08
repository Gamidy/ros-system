"""消息推送统一接口"""
import logging
from typing import Optional

from app.services.notification.channels import (
    MessageChannel,
    WeComChannel,
    DingTalkChannel,
)

logger = logging.getLogger(__name__)

# 通道类型 → 实现类映射
_CHANNEL_MAP = {
    "wecom": WeComChannel,
    "dingtalk": DingTalkChannel,
}


def send(
    channel_type: str,
    content: str,
    *,
    webhook_url: str,
    secret: str = "",
    daily_limit: int = 1000,
    channel_id: Optional[int] = None,
) -> dict:
    """统一消息发送入口

    Args:
        channel_type:  通道类型 (wecom / dingtalk)
        content:       消息正文（纯文本）
        webhook_url:   Webhook 机器人地址
        secret:        签名密钥（钉钉必填）
        daily_limit:   每日发送上限（默认 1000）
        channel_id:    通道 ID（用于日志 / 限额计数，None 时自动生成）

    Returns:
        {"ok": bool, "msg": str}
    """
    cls = _CHANNEL_MAP.get(channel_type)
    if cls is None:
        return {"ok": False, "msg": f"Unsupported channel type: {channel_type}"}

    if channel_id is None:
        channel_id = hash(webhook_url) & 0x7FFFFFFF

    instance: MessageChannel = cls(
        channel_id=channel_id,
        webhook_url=webhook_url,
        secret=secret,
        daily_limit=daily_limit,
    )
    return instance.do_send(content)


__all__ = ["send", "MessageChannel", "WeComChannel", "DingTalkChannel"]
