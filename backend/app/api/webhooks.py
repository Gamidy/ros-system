"""Webhook 订阅与投递管理 API

提供 Webhook 订阅的 CRUD 接口以及投递日志查询与重试功能。
- GET 接口使用 Depends(get_current_user) 认证
- 写操作使用 Depends(require_role(...)) 权限控制
- 所有数据库查询使用参数化查询，防止 SQL 注入
"""
import asyncio
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.webhook import WebhookDeliveryLog, WebhookSubscription
from app.services.webhook_service import webhook_dispatcher

router = APIRouter(prefix="/api/webhooks", tags=["Webhook通知系统"])


# ════════════════════════════════════════════════════════
# Pydantic 请求/响应 Schema
# ════════════════════════════════════════════════════════


class WebhookSubscriptionCreate(BaseModel):
    """创建 Webhook 订阅请求体"""
    name: str = Field(..., min_length=1, max_length=100, description="订阅名称")
    url: str = Field(..., min_length=1, max_length=500, description="回调URL")
    events: list[str] = Field(..., min_length=1, description="订阅的事件类型列表，如 [\"plan.approved\", \"test.done_with_ng\"]")
    secret: Optional[str] = Field(None, max_length=128, description="HMAC-SHA256 签名密钥")
    is_active: bool = True


class WebhookSubscriptionUpdate(BaseModel):
    """更新 Webhook 订阅请求体（全部字段可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    events: Optional[list[str]] = None
    secret: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None


class WebhookSubscriptionOut(BaseModel):
    """Webhook 订阅响应模型"""
    id: int
    org_id: Optional[int] = None
    name: str
    url: str
    events: list
    secret: Optional[str] = None
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookDeliveryLogOut(BaseModel):
    """Webhook 投递日志响应模型"""
    id: int
    subscription_id: int
    event_type: str
    payload: Optional[str] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    success: bool
    attempted_at: Optional[datetime] = None
    retry_count: int = 0

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════
# 订阅管理 API
# ════════════════════════════════════════════════════════


@router.post("/subscriptions", response_model=WebhookSubscriptionOut)
def create_subscription(
    req: WebhookSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """创建 Webhook 订阅

    需要 admin / general_manager / rd_director / project_admin / product_manager 角色。
    自动将当前用户的 org_id 绑定到订阅。
    """
    subscription = WebhookSubscription(
        org_id=getattr(current_user, "org_id", None),
        name=req.name,
        url=req.url,
        events=req.events,
        secret=req.secret,
        is_active=req.is_active,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/subscriptions", response_model=list[WebhookSubscriptionOut])
def list_subscriptions(
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list:
    """获取 Webhook 订阅列表

    支持按 is_active 筛选，按创建时间降序排列。
    所有已登录用户可查看。
    """
    query = db.query(WebhookSubscription)
    if is_active is not None:
        query = query.filter(WebhookSubscription.is_active == is_active)
    return query.order_by(WebhookSubscription.created_at.desc()).all()


@router.patch("/subscriptions/{sub_id}", response_model=WebhookSubscriptionOut)
def update_subscription(
    sub_id: int,
    req: WebhookSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """更新 Webhook 订阅

    仅更新请求中显式设置的字段（PATCH 语义）。
    """
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub, field, value)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/subscriptions/{sub_id}")
def delete_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """删除 Webhook 订阅

    硬删除，同时级联的投递日志不受影响。
    """
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    db.delete(sub)
    db.commit()
    return {"ok": True, "message": "订阅已删除"}


@router.post("/subscriptions/{sub_id}/test")
def test_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """发送测试事件到指定订阅

    构造一个 ``test.webhook`` 事件，通过 WebhookDispatcher 异步发送。
    不会记录到事件总线，仅用于验证订阅 URL 可达性。
    """
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    test_payload = {
        "test": True,
        "message": "这是一条 ROS Webhook 测试通知",
        "subscription_name": sub.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 尝试在当前事件循环中创建异步任务
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(webhook_dispatcher.dispatch("test.webhook", test_payload))
        else:
            loop.run_until_complete(webhook_dispatcher.dispatch("test.webhook", test_payload))
    except RuntimeError:
        t = threading.Thread(
            target=lambda: asyncio.run(webhook_dispatcher.dispatch("test.webhook", test_payload)),
            daemon=True,
        )
        t.start()

    return {"ok": True, "message": "测试事件已发送，请检查目标 URL 是否收到请求"}


# ════════════════════════════════════════════════════════
# 投递日志 API
# ════════════════════════════════════════════════════════


@router.get("/deliveries", response_model=list[WebhookDeliveryLogOut])
def list_deliveries(
    subscription_id: Optional[int] = Query(None, description="按订阅ID过滤"),
    success: Optional[bool] = Query(None, description="按成功状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回条数（最多200）"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list:
    """获取 Webhook 投递日志列表

    支持按 subscription_id、success 过滤，按投递时间降序排列。
    所有已登录用户可查看。
    """
    query = db.query(WebhookDeliveryLog)
    if subscription_id is not None:
        query = query.filter(WebhookDeliveryLog.subscription_id == subscription_id)
    if success is not None:
        query = query.filter(WebhookDeliveryLog.success == success)
    return query.order_by(WebhookDeliveryLog.attempted_at.desc()).limit(limit).all()


@router.post("/deliveries/{delivery_id}/retry")
def retry_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """手动重试失败的投递

    调用 WebhookDispatcher.retry_failed() 同步重试并更新投递日志。
    """
    delivery = db.query(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="投递记录不存在")

    success = webhook_dispatcher.retry_failed(delivery_id)
    return {
        "ok": success,
        "message": "重试成功" if success else "重试失败，请检查目标 URL",
    }
