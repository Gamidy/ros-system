"""审批催办 Celery 定时任务 — Periodically scan pending approvals"""
import logging

from app.workers.celery_app import celery_app
from app.services.approval_reminder import scan_and_remind

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=30,
    name="scan_approval_reminders",
)
def scan_approval_reminders(self):
    """扫描 pending 审批，超时自动催办"""
    try:
        scan_and_remind()
        logger.info("审批催办扫描完成")
    except Exception as e:
        logger.exception("审批催办扫描失败")
        raise self.retry(exc=e)
