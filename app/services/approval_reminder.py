"""审批催办服务 — 定时扫描pending审批，超时自动通知

规则:
  - 提交超过 24 小时未完成审批 → 通知审批人
  - 提交超过 48 小时未完成审批 → 升级通知研发总监
"""
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.approval import ApprovalRequest, ApprovalRecord, ApprovalStep
from app.models.user import User
from app.models.alert import Notification

logger = logging.getLogger(__name__)


def _create_notification(
    db: Session,
    target_user_id: int,
    title: str,
    content: str,
    channel: str = "system",
):
    """创建系统通知记录"""
    notif = Notification(
        target_user=str(target_user_id),
        channel=channel,
        title=title,
        content=content,
    )
    db.add(notif)
    db.flush()


def scan_and_remind():
    """扫描所有 pending 状态的审批, 按规则催办"""
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        threshold_24h = now - timedelta(hours=24)
        threshold_48h = now - timedelta(hours=48)

        # 查询所有进行中的产品策划审批
        pending_requests = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.status == "pending",
                ApprovalRequest.request_type == "proposal",
            )
            .all()
        )

        for ar in pending_requests:
            if ar.created_at is None:
                continue

            # ── 超过 48 小时, 升级通知研发总监 ──
            if ar.created_at <= threshold_48h:
                # 通知研发总监
                director = (
                    db.query(User)
                    .filter(User.role == "rd_director", User.is_active == True)
                    .first()
                )
                if director:
                    _create_notification(
                        db,
                        target_user_id=director.id,
                        title=f"【升级催办】审批超48小时: {ar.title}",
                        content=(
                            f"项目「{ar.title}」的立项审批已提交超过 48 小时仍未完成。"
                            f"请关注并推动审批流程。"
                        ),
                    )
                    logger.info(f"审批 {ar.id} 已升级通知研发总监")

            # ── 超过 24 小时, 通知审批人 ──
            elif ar.created_at <= threshold_24h:
                # 查询当前步骤中 pending 的审批人
                current_record = (
                    db.query(ApprovalRecord)
                    .filter(
                        ApprovalRecord.request_id == ar.id,
                        ApprovalRecord.decision == "pending",
                    )
                    .first()
                )
                if current_record:
                    _create_notification(
                        db,
                        target_user_id=int(current_record.approver) if current_record.approver.isdigit() else 0,
                        title=f"【审批催办】待审批: {ar.title}",
                        content=(
                            f"项目「{ar.title}」的立项审批已提交超过 24 小时，"
                            f"请您尽快完成审批。"
                        ),
                    )

                logger.info(f"审批 {ar.id} 已发送24h催办通知")

        db.commit()
        logger.info(f"审批催办扫描完成, 共处理 {len(pending_requests)} 条记录")

    except Exception as e:
        logger.exception("unexpected error")
        db.rollback()
        logger.error(f"审批催办扫描异常: {e}")
