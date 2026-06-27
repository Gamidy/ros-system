"""Webhook 订阅管理 API

提供 Webhook 订阅的完整 CRUD 接口以及测试发送和日志查询功能。
- GET /api/webhooks — 列出所有订阅
- POST /api/webhooks — 创建订阅
- GET /api/webhooks/{id} — 查询单个
- PUT /api/webhooks/{id} — 更新
- DELETE /api/webhooks/{id} — 删除
- POST /api/webhooks/{id}/test — 发送测试事件
- GET /api/webhooks/{id}/logs — 查看发送日志
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.webhook_subscription import WebhookSubscription
from app.models.webhook import WebhookDeliveryLog
from app.services.webhook_service import webhook_dispatcher

router = APIRouter(prefix="/api/webhooks", tags=["Webhook订阅管理"])


# ════════════════════════════════════════════════════════
# Pydantic Schema
# ════════════════════════════════════════════════════════


class WebhookSubscriptionCreate(BaseModel):
    """创建 Webhook 订阅请求体"""
    name: str = Field(..., min_length=1, max_length=100, description="订阅名称")
    url: str = Field(..., min_length=1, max_length=500, description="目标回调URL")
    event_type: str = Field(..., min_length=1, max_length=100, description="订阅的事件类型，如 'plan.approved'")
    secret: Optional[str] = Field(None, max_length=255, description="HMAC-SHA256 签名密钥")
    enabled: bool = True


class WebhookSubscriptionUpdate(BaseModel):
    """更新 Webhook 订阅请求体（全部可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    event_type: Optional[str] = Field(None, min_length=1, max_length=100)
    secret: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None


class WebhookSubscriptionOut(BaseModel):
    """Webhook 订阅响应模型"""
    id: int
    name: str
    url: str
    event_type: str
    secret: Optional[str] = None
    enabled: bool
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("secret")
    def mask_secret(self, v: Optional[str]) -> Optional[str]:
        return None

    class Config:
        from_attributes = True


class WebhookLogOut(BaseModel):
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
# 订阅 CRUD
# ════════════════════════════════════════════════════════


@router.get("", response_model=list[WebhookSubscriptionOut])
def list_subscriptions(
    enabled: Optional[bool] = Query(None, description="按启用状态过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "quality_engineer", "rd_director")),
) -> list[WebhookSubscriptionOut]:
    """获取所有 Webhook 订阅列表"""
    query = db.query(WebhookSubscription)
    if enabled is not None:
        query = query.filter(WebhookSubscription.enabled == enabled)
    return query.order_by(desc(WebhookSubscription.created_at)).all()


@router.post("", response_model=WebhookSubscriptionOut, status_code=201)
def create_subscription(
    req: WebhookSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> WebhookSubscriptionOut:
    """创建 Webhook 订阅"""
    sub = WebhookSubscription(
        name=req.name,
        url=req.url,
        event_type=req.event_type,
        secret=req.secret,
        enabled=req.enabled,
        created_by=getattr(current_user, "username", None) or str(getattr(current_user, "id", "")),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/{sub_id}", response_model=WebhookSubscriptionOut)
def get_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "quality_engineer", "rd_director")),
) -> WebhookSubscriptionOut:
    """查询单个 Webhook 订阅"""
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return sub


@router.put("/{sub_id}", response_model=WebhookSubscriptionOut)
def update_subscription(
    sub_id: int,
    req: WebhookSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> WebhookSubscriptionOut:
    """更新 Webhook 订阅（全量覆盖，仅更新传入字段）"""
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub, field, value)
    sub.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{sub_id}")
def delete_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """删除 Webhook 订阅"""
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    db.delete(sub)
    db.commit()
    return {"ok": True, "message": "订阅已删除"}


# ════════════════════════════════════════════════════════
# 测试 & 日志
# ════════════════════════════════════════════════════════


@router.post("/{sub_id}/test")
def test_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        "admin", "general_manager", "rd_director",
        "project_admin", "product_manager",
    )),
) -> dict:
    """发送测试事件到指定订阅"""
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    result = webhook_dispatcher.send_test(sub)
    if result.get("success"):
        return {"ok": True, "message": "测试事件已发送，目标URL返回成功"}
    return {"ok": False, "message": f"测试事件发送失败: {result.get('error', '未知错误')}"}


@router.get("/{sub_id}/logs", response_model=list[WebhookLogOut])
def get_subscription_logs(
    sub_id: int,
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "quality_engineer", "rd_director")),
) -> list[WebhookLogOut]:
    """查看指定订阅的发送日志"""
    # 验证订阅存在
    sub = db.query(WebhookSubscription).filter(WebhookSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    logs = webhook_dispatcher.get_logs(sub_id, limit=limit)
    return logs
