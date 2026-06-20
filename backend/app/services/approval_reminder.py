"""审批催办服务 — 定时扫描pending审批，超时自动通知

规则:
  - 提交超过 24 小时未完成审批 → 通知审批人 (reminded=True)
  - 提交超过 48 小时未完成审批 → 升级通知研发总监 (escalated=True)
"""
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.proposal_approval import ProposalApproval
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

        # 查询所有进行中的审批
        pending_approvals = (
            db.query(ProposalApproval)
            .filter(
                ProposalApproval.status.in_(["pending_parallel", "pending_director"])
            )
            .all()
        )

        for pa in pending_approvals:
            if pa.created_at is None:
                continue

            # ── 超过 48 小时, 升级通知研发总监 ──
            if pa.created_at <= threshold_48h and not pa.escalated:
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
                        title=f"【升级催办】审批超48小时: {pa.title}",
                        content=(
                            f"项目「{pa.title}」的立项审批已提交超过 48 小时仍未完成。"
                            f"当前状态: {pa.status}。请关注并推动审批流程。"
                        ),
                    )
                    logger.info(f"审批 {pa.id} 已升级通知研发总监")

                pa.escalated = True
                pa.reminded = True  # 同时标记已催办

            # ── 超过 24 小时, 通知审批人 ──
            elif pa.created_at <= threshold_24h and not pa.reminded:
                # 通知还 pending 的审批人
                if pa.status == "pending_parallel" and pa.parallel_reviewers:
                    for reviewer in pa.parallel_reviewers:
                        if reviewer.get("status") == "pending":
                            _create_notification(
                                db,
                                target_user_id=reviewer["user_id"],
                                title=f"【审批催办】待审批: {pa.title}",
                                content=(
                                    f"项目「{pa.title}」的立项审批已提交超过 24 小时，"
                                    f"请您尽快完成审批。"
                                ),
                            )

                elif pa.status == "pending_director" and pa.director_reviewer_id:
                    _create_notification(
                        db,
                        target_user_id=pa.director_reviewer_id,
                        title=f"【审批催办】待终审: {pa.title}",
                        content=(
                            f"项目「{pa.title}」的研发总监终审已等待超过 24 小时，"
                            f"请您尽快完成审批。"
                        ),
                    )

                pa.reminded = True
                logger.info(f"审批 {pa.id} 已发送24h催办通知")

        db.commit()
        logger.info(f"审批催办扫描完成, 共处理 {len(pending_approvals)} 条记录")

    except Exception as e:
        db.rollback()
        logger.error(f"审批催办扫描异常: {e}")
    finally:
        db.close()
