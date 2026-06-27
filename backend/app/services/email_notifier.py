"""审批邮件通知 — 离线提醒申请人审批状态变更

通过 SMTP 发送 HTML 格式邮件。
配置通过环境变量读取：
  SMTP_HOST        (默认 smtp.qq.com)
  SMTP_PORT        (默认 465)
  SMTP_USER
  SMTP_PASSWORD
  NOTIFY_EMAIL_FROM  (发件人地址)
  NOTIFY_EMAIL_TO    (默认收件人，当查询不到申请人邮箱时使用)
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.database import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)

# ── 邮件配置（环境变量） ──────────────────────────────

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL_FROM = os.getenv("NOTIFY_EMAIL_FROM", "")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")


def _build_html_body(
    title: str,
    status: str,
    request_id: int,
    comment: str,
    timestamp: str,
) -> str:
    """构建 HTML 邮件正文"""
    status_label = "✅ 已通过" if status == "approved" else "❌ 已驳回"
    status_color = "#52c41a" if status == "approved" else "#ff4d4f"

    return f"""\
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'PingFang SC','Microsoft YaHei',Arial,sans-serif; background:#f5f5f5; padding:24px;">
<div style="max-width:560px; margin:0 auto; background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); overflow:hidden;">
  <div style="background:{status_color}; padding:20px 24px; text-align:center;">
    <h2 style="color:#fff; margin:0; font-size:18px;">📋 审批通知</h2>
  </div>
  <div style="padding:24px;">
    <p style="margin:0 0 16px; font-size:15px; color:#333;">
      您的审批「<strong>{title}</strong>」状态已更新为：
      <span style="color:{status_color}; font-weight:bold;">{status_label}</span>
    </p>
    <table style="width:100%; border-collapse:collapse; font-size:14px;">
      <tr><td style="padding:8px 12px; background:#fafafa; color:#666; width:80px;">审批编号</td>
          <td style="padding:8px 12px;">{request_id}</td></tr>
      <tr><td style="padding:8px 12px; background:#fafafa; color:#666;">审批结果</td>
          <td style="padding:8px 12px; color:{status_color}; font-weight:bold;">{status_label}</td></tr>
      <tr><td style="padding:8px 12px; background:#fafafa; color:#666;">审批意见</td>
          <td style="padding:8px 12px;">{comment or "无"}</td></tr>
      <tr><td style="padding:8px 12px; background:#fafafa; color:#666;">通知时间</td>
          <td style="padding:8px 12px;">{timestamp}</td></tr>
    </table>
  </div>
  <div style="background:#fafafa; padding:12px 24px; text-align:center; border-top:1px solid #eee;">
    <p style="margin:0; font-size:12px; color:#999;">此为系统自动发送的审批通知邮件，请勿回复。</p>
  </div>
</div>
</body>
</html>"""


def _get_user_email(username: str) -> Optional[str]:
    """从 User 模型查询申请人邮箱"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and user.email:
            return user.email
        return None
    except Exception as e:
        logger.warning("查询用户邮箱失败: username=%s, error=%s", username, e)
        return None
    finally:
        db.close()


def send_approval_email(
    *,
    requester: str,
    title: str,
    status: str,
    request_id: int,
    comment: str = "",
) -> None:
    """发送审批结果邮件通知给申请人

    通过 smtplib (SSL) 发送 HTML 邮件。
    如果 SMTP 未配置或发送失败，仅记录日志，不抛出异常。

    Args:
        requester:  申请人用户名（用于查询邮箱）
        title:      审批标题
        status:     审批状态 (approved / rejected)
        request_id: 审批请求 ID
        comment:    审批意见
    """
    # ── 前置检查：SMTP 是否已配置 ──
    if not SMTP_USER or not SMTP_PASSWORD or not NOTIFY_EMAIL_FROM:
        logger.info(
            "邮件通知未配置 (SMTP_USER/PASSWORD/FROM)，跳过: "
            "requester=%s, title=%s",
            requester, title,
        )
        return

    # ── 确定收件人地址 ──
    to_email = _get_user_email(requester) or NOTIFY_EMAIL_TO
    if not to_email:
        logger.warning(
            "无法确定收件人邮箱 (requester=%s 无 email 字段，且 NOTIFY_EMAIL_TO 未设置)，跳过",
            requester,
        )
        return

    # ── 构建邮件 ──
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"审批通知 - {title}"

    html = _build_html_body(title, status, request_id, comment, timestamp)

    msg = MIMEMultipart("alternative")
    msg["From"] = NOTIFY_EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html", "utf-8"))

    # ── 发送 ──
    try:
        if SMTP_PORT == 465:
            # SSL 模式
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(NOTIFY_EMAIL_FROM, [to_email], msg.as_string())
        else:
            # STARTTLS 模式
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(NOTIFY_EMAIL_FROM, [to_email], msg.as_string())

        logger.info(
            "审批邮件发送成功: requester=%s, to=%s, title=%s, status=%s",
            requester, to_email, title, status,
        )
    except smtplib.SMTPException as e:
        logger.error(
            "审批邮件发送失败(SMTP): requester=%s, to=%s, error=%s",
            requester, to_email, e,
        )
    except Exception as e:
        logger.error(
            "审批邮件发送失败: requester=%s, to=%s, error=%s",
            requester, to_email, e,
        )


__all__ = ["send_approval_email"]
