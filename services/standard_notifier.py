"""标准监控 — 变更通知服务

检测到新标准/更新时，通过站内信 + 企业微信推送给所有产品经理角色用户。
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def notify_standard_update(
    db: Session,
    region_id: int,
    region_name: str,
    stats: dict,
    crawl_id: Optional[int] = None,
) -> int:
    """标准爬取完成后，推送变更通知给所有 PM 角色用户

    Args:
        db: 数据库会话
        region_id: 地区 ID
        region_name: 地区中文名
        stats: {"new_added": int, "updated": int, "skipped": int}
        crawl_id: 关联爬取日志 ID

    Returns:
        int: 通知推送人数
    """
    from app.models.user import User
    from app.models.notification_log import NotificationLog

    new_count = stats.get("new_added", 0)
    updated_count = stats.get("updated", 0)

    if new_count == 0 and updated_count == 0:
        return 0

    # 查找所有 product_manager 角色用户
    pms = db.query(User).filter(
        User.role == "product_manager",
        User.is_active.is_(True),
    ).all()

    if not pms:
        logger.info("标准更新通知: 无产品经理用户，跳过")
        return 0

    # 构造消息
    title = f"📋 {region_name} 标准更新提醒"
    parts: list[str] = []
    if new_count > 0:
        parts.append(f"新增 {new_count} 条")
    if updated_count > 0:
        parts.append(f"更新 {updated_count} 条")
    content = f"{region_name} 检测到 {'，'.join(parts)}。请前往标准知识库查看详情。"

    # 写入站内信通知日志
    request_id = f"std_{region_name}_{datetime.now():%Y%m%d}"
    for pm in pms:
        notif = NotificationLog(
            request_id=request_id,
            channel="system",
            event_type="standard_update",
            status="sent",
        )
        db.add(notif)
    db.commit()

    # 推送企业微信（如果配置了）
    _try_wecom_push(db, title, content)

    logger.info("标准更新通知: %d 人 (%s)", len(pms), content)
    return len(pms)


def _try_wecom_push(db: Session, title: str, content: str) -> bool:
    """尝试推送到企业微信（静默失败）"""
    try:
        from app.models.notification_channel import NotificationChannel
        from app.services.notification.channels import WeComChannel

        channel = db.query(NotificationChannel).filter(
            NotificationChannel.channel_type == "wecom",
            NotificationChannel.enabled.is_(True),
            NotificationChannel.status == "active",
        ).first()

        if not channel:
            return False

        wecom = WeComChannel(
            channel_id=channel.id,
            webhook_url=channel.webhook_url,
            secret=channel.secret or "",
        )

        md_content = f"### {title}\n\n{content}\n\n[查看详情]({channel.webhook_url})"
        result = wecom.send(md_content)
        return result.get("ok", False)
    except Exception as exc:
        logger.warning("企业微信推送失败: %s", exc)
        return False
