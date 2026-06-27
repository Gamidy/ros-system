"""企业微信 / 钉钉机器人通知测试 API

提供测试端点验证 Webhook 通道是否配置正确。
- POST /api/notifications/test/wecom
- POST /api/notifications/test/dingtalk
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.notification_channel import NotificationChannel
from app.services.notification import send as notification_send

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["通知测试"])


class TestNotificationIn(BaseModel):
    """测试通知请求体"""
    message: str = Field("这是一条 ROS 系统测试通知", description="测试消息内容")
    channel_id: int | None = Field(None, description="通道 ID（不传则使用第一个启用的对应类型通道）")


class TestNotificationOut(BaseModel):
    """测试通知响应体"""
    ok: bool
    msg: str
    channel_type: str
    channel_name: str | None = None


def _get_channel_or_first(
    db: Session,
    channel_type: str,
    channel_id: int | None,
) -> NotificationChannel | None:
    """根据 channel_id 或 channel_type 查找启用的通知通道"""
    if channel_id is not None:
        return (
            db.query(NotificationChannel)
            .filter(
                NotificationChannel.id == channel_id,
                NotificationChannel.channel_type == channel_type,
                NotificationChannel.enabled == True,
            )
            .first()
        )
    return (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.channel_type == channel_type,
            NotificationChannel.enabled == True,
        )
        .first()
    )


@router.post("/test/wecom", response_model=TestNotificationOut)
def test_wecom(
    body: TestNotificationIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> TestNotificationOut:
    """发送测试消息到企业微信群机器人"""
    channel = _get_channel_or_first(db, "wecom", body.channel_id)
    if channel is None:
        return TestNotificationOut(
            ok=False,
            msg="未找到已启用的企微通知通道",
            channel_type="wecom",
        )

    result = notification_send(
        channel_type="wecom",
        content=body.message,
        webhook_url=channel.webhook_url,
        secret=channel.secret or "",
        daily_limit=channel.daily_limit,
        channel_id=channel.id,
    )
    logger.info(
        "测试企微通知: channel_id=%s, channel_name=%s, result=%s",
        channel.id, channel.name, result,
    )
    return TestNotificationOut(
        ok=result.get("ok", False),
        msg=result.get("msg", ""),
        channel_type="wecom",
        channel_name=channel.name,
    )


@router.post("/test/dingtalk", response_model=TestNotificationOut)
def test_dingtalk(
    body: TestNotificationIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> TestNotificationOut:
    """发送测试消息到钉钉自定义机器人"""
    channel = _get_channel_or_first(db, "dingtalk", body.channel_id)
    if channel is None:
        return TestNotificationOut(
            ok=False,
            msg="未找到已启用的钉钉通知通道",
            channel_type="dingtalk",
        )

    result = notification_send(
        channel_type="dingtalk",
        content=body.message,
        webhook_url=channel.webhook_url,
        secret=channel.secret or "",
        daily_limit=channel.daily_limit,
        channel_id=channel.id,
    )
    logger.info(
        "测试钉钉通知: channel_id=%s, channel_name=%s, result=%s",
        channel.id, channel.name, result,
    )
    return TestNotificationOut(
        ok=result.get("ok", False),
        msg=result.get("msg", ""),
        channel_type="dingtalk",
        channel_name=channel.name,
    )


__all__ = ["router", "TestNotificationIn", "TestNotificationOut"]
