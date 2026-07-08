"""
ECO BOM 更新 Celery Worker — Board 裁决重试队列
ECO EFFECTIVE → BOM Update → Retry(3次) → ROLLBACK_REQUIRED
"""
import logging

from app.workers.celery_app import celery_app
from app.services.eco_bom_service import apply_bom_update, rollback_bom_update

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,   # 初始 10 秒
    acks_late=True,
    queue="critical",
    autoretry_for=(Exception,),
)
def eco_effective_bom_update(self, eco_id: int):
    """
    ECO EFFECTIVE 触发 BOM 更新
    Board 裁决: max_retries=3, exponential backoff

    Saga:
    1. Update BOM
    2. Success → CLOSED
    3. Fail → Retry (3 times) → ROLLBACK_REQUIRED → notify engineering
    """
    logger.info("[eco_effective_bom_update] ECO %s: 开始 BOM 更新 (尝试 %d/4)",
                eco_id, self.request.retries + 1)

    success = apply_bom_update(eco_id)

    if success:
        logger.info("[eco_effective_bom_update] ECO %s: BOM 更新成功", eco_id)
        # TODO: 触发 ECO → CLOSED 自动推进
        return {"eco_id": eco_id, "status": "bom_updated", "attempts": self.request.retries + 1}

    # 重试耗尽 → 进入 ROLLBACK_REQUIRED 状态
    if self.request.retries >= 3:
        logger.error("[eco_effective_bom_update] ECO %s: 3次重试耗尽，触发回滚", eco_id)
        rollback_bom_update(eco_id)
        # TODO: 状态推进 → ROLLBACK_REQUIRED
        # from app.services.eco_bom_service import set_eco_status
        # set_eco_status(eco_id, "rollback_required")
        return {"eco_id": eco_id, "status": "rollback_required", "attempts": 4}

    raise self.retry(exc=Exception(f"ECO {eco_id} BOM 更新失败 (尝试 {self.request.retries + 1})"))
