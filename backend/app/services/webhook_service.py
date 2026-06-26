"""Webhook 事件驱动推送服务

提供 WebhookDispatcher 单例，用于:
- 根据事件类型查询匹配的订阅，并发推送 HTTP POST 请求
- HMAC-SHA256 签名验证
- 指数退避重试 (1s → 4s → 16s，最多3次)
- 失败的投递日志手动重试
"""
import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.webhook import WebhookDeliveryLog, WebhookSubscription

logger = logging.getLogger(__name__)

# 指数退避间隔（秒）
RETRY_DELAYS = [1, 4, 16]
MAX_RETRIES = 3


class WebhookDispatcher:
    """Webhook 分发器 — 事件驱动，并发推送

    单例模式，通过模块级 ``webhook_dispatcher`` 引用。
    所有推送使用 httpx.AsyncClient 异步发送。
    """

    async def dispatch(self, event_type: str, payload: Dict[str, Any]) -> None:
        """根据事件类型查询匹配的启用的订阅，并发推送

        遍历匹配的订阅列表，为每个订阅创建异步推送任务，
        使用 ``asyncio.gather`` 并发执行。

        Args:
            event_type: 事件类型字符串（如 ``"plan.approved"``）
            payload: 事件载荷字典
        """
        db: Session = SessionLocal()
        try:
            subscriptions = (
                db.query(WebhookSubscription)
                .filter(
                    WebhookSubscription.is_active == True,
                    # 使用 JSON_CONTAINS 语义：events JSON 列中包含 event_type
                    WebhookSubscription.events.as_string().contains(event_type),
                )
                .all()
            )
        except Exception as e:
            logger.warning(f"通过JSON查询Webhook订阅失败: {e}")
            # MySQL JSON_CONTAINS 或 SQLite JSON 兼容
            # Fallback：全量读取后过滤（兼容 SQLite 开发环境）
            try:
                all_subs = (
                    db.query(WebhookSubscription)
                    .filter(WebhookSubscription.is_active == True)
                    .all()
                )
                subscriptions = [s for s in all_subs if event_type in (s.events or [])]
            except Exception as fallback_e:
                logger.error("查询 webhook 订阅失败: %s", fallback_e)
                return
        finally:
            db.close()

        if not subscriptions:
            logger.debug("Webhook 无匹配订阅: event_type=%s", event_type)
            return

        logger.info(
            "Webhook dispatch: event=%s, matched=%d 订阅",
            event_type, len(subscriptions),
        )

        # 并发推送所有匹配的订阅
        tasks = [
            self._send_to_subscription(sub, event_type, payload)
            for sub in subscriptions
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_subscription(
        self,
        subscription: WebhookSubscription,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """向单个订阅发送 webhook（含指数退避重试）

        序列化 payload → 签名 → POST → 记录日志。
        失败后按 1s → 4s → 16s 退避重试。

        Args:
            subscription: WebhookSubscription 实例
            event_type: 事件类型
            payload: 事件载荷
        """
        # 序列化载荷，包含 event_type 元信息
        body = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload_str = json.dumps(body, ensure_ascii=False, default=str)
        signature = self._sign_payload(payload_str, subscription.secret or "")

        last_error: Optional[str] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                status_code, response_body = await self._send_webhook(
                    url=subscription.url,
                    payload=payload_str,
                    signature=signature,
                )
                success = 200 <= status_code < 300

                self._log_delivery(
                    subscription_id=subscription.id,
                    event_type=event_type,
                    payload=payload_str,
                    response_status=status_code,
                    response_body=response_body,
                    success=success,
                    retry_count=attempt - 1,
                )

                if success:
                    self._update_last_triggered(subscription.id)
                    logger.info(
                        "Webhook 推送成功: sub_id=%s, url=%s, event=%s, attempt=%d",
                        subscription.id, subscription.url, event_type, attempt,
                    )
                    return

                last_error = f"HTTP {status_code}: {response_body[:200]}"
                logger.warning(
                    "Webhook 推送失败 (attempt %d/%d): sub_id=%s, %s",
                    attempt, MAX_RETRIES, subscription.id, last_error,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Webhook 推送异常 (attempt %d/%d): sub_id=%s, error=%s",
                    attempt, MAX_RETRIES, subscription.id, last_error,
                )

            # 指数退避（最后一次不等待）
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt - 1] if attempt - 1 < len(RETRY_DELAYS) else 16
                await asyncio.sleep(delay)

        # 所有重试均失败
        logger.error(
            "Webhook 推送最终失败: sub_id=%s, url=%s, event=%s, error=%s",
            subscription.id, subscription.url, event_type, last_error,
        )

    def _sign_payload(self, payload: str, secret: str) -> str:
        """HMAC-SHA256 签名

        使用 secret 密钥对 payload 进行 HMAC-SHA256 签名，
        结果以十六进制字符串返回，放入 ``X-ROS-Signature`` 请求头。

        Args:
            payload: JSON 字符串形式的请求体
            secret: 签名密钥

        Returns:
            HMAC-SHA256 十六进制签名字符串；secret 为空时返回空字符串
        """
        if not secret:
            return ""
        h = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        )
        return h.hexdigest()

    async def _send_webhook(
        self,
        url: str,
        payload: str,
        signature: str,
    ) -> tuple[int, str]:
        """通过 httpx.AsyncClient 异步发送 HTTP POST 请求

        Args:
            url: 目标回调 URL
            payload: JSON 格式的请求体字符串
            signature: HMAC 签名（通过 X-ROS-Signature 请求头传递）

        Returns:
            (status_code, response_body) 元组
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ROS-Webhook/1.0",
        }
        if signature:
            headers["X-ROS-Signature"] = signature

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, content=payload, headers=headers)
            body = response.text
            return response.status_code, body

    def retry_failed(self, delivery_id: int) -> bool:
        """重试失败的投递记录

        根据投递日志 ID 找到原始订阅和载荷，重新发送一次。
        更新投递日志的 retry_count、response_status、response_body、success。

        Args:
            delivery_id: WebhookDeliveryLog 的 ID

        Returns:
            重试是否成功（HTTP 2xx）
        """
        db: Session = SessionLocal()
        try:
            delivery = (
                db.query(WebhookDeliveryLog)
                .filter(WebhookDeliveryLog.id == delivery_id)
                .first()
            )
            if not delivery:
                logger.warning("投递记录不存在: delivery_id=%s", delivery_id)
                return False

            subscription = (
                db.query(WebhookSubscription)
                .filter(WebhookSubscription.id == delivery.subscription_id)
                .first()
            )
            if not subscription:
                logger.warning("订阅记录不存在: sub_id=%s", delivery.subscription_id)
                return False

            # 同步发送（retry_failed 是同步方法）
            signature = self._sign_payload(delivery.payload, subscription.secret or "")
            try:
                import httpx as sync_httpx
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "ROS-Webhook/1.0",
                }
                if signature:
                    headers["X-ROS-Signature"] = signature

                response = sync_httpx.post(
                    subscription.url,
                    content=delivery.payload,
                    headers=headers,
                    timeout=30.0,
                )
                success = 200 <= response.status_code < 300

                delivery.retry_count = (delivery.retry_count or 0) + 1
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:500]
                delivery.success = success
                delivery.attempted_at = datetime.now(timezone.utc)
                db.commit()

                if success:
                    self._update_last_triggered(subscription.id)
                    logger.info(
                        "重试成功: delivery_id=%s, status=%s",
                        delivery_id, response.status_code,
                    )
                else:
                    logger.warning(
                        "重试仍失败: delivery_id=%s, status=%s",
                        delivery_id, response.status_code,
                    )

                return success

            except Exception as e:
                delivery.retry_count = (delivery.retry_count or 0) + 1
                delivery.success = False
                delivery.response_body = str(e)[:500]
                delivery.attempted_at = datetime.now(timezone.utc)
                db.commit()
                logger.error("重试异常: delivery_id=%s, error=%s", delivery_id, e)
                return False

        finally:
            db.close()

    def _log_delivery(
        self,
        subscription_id: int,
        event_type: str,
        payload: str,
        response_status: int,
        response_body: str,
        success: bool,
        retry_count: int,
    ) -> None:
        """记录一次投递日志到数据库

        Args:
            subscription_id: 关联的订阅 ID
            event_type: 事件类型
            payload: 请求体 JSON 字符串
            response_status: 响应状态码
            response_body: 响应体（截取前 500 字符）
            success: 是否成功
            retry_count: 当前是第几次重试
        """
        db: Session = SessionLocal()
        try:
            log_entry = WebhookDeliveryLog(
                subscription_id=subscription_id,
                event_type=event_type,
                payload=payload,
                response_status=response_status,
                response_body=response_body[:500],
                success=success,
                retry_count=retry_count,
                attempted_at=datetime.now(timezone.utc),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error("投递日志记录失败: %s", e)
        finally:
            db.close()

    def _update_last_triggered(self, subscription_id: int) -> None:
        """更新订阅的最后触发时间为当前时间

        Args:
            subscription_id: 订阅 ID
        """
        db: Session = SessionLocal()
        try:
            sub = (
                db.query(WebhookSubscription)
                .filter(WebhookSubscription.id == subscription_id)
                .first()
            )
            if sub:
                sub.last_triggered_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as e:
            logger.warning("更新 last_triggered_at 失败: %s", e)
        finally:
            db.close()


# 模块级单例
webhook_dispatcher = WebhookDispatcher()
