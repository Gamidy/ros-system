"""add_notification_channels — 创建消息推送通道配置表

通知多渠道聚合基础 D6-1。
创建 notification_channels 表用于存储企微/钉钉机器人 Webhook 配置。

Revision ID: 20260627_add_notification_channels
Revises: 20260627_add_product_plan_version_history, 20260626_add_workflow_transition_specs
Create Date: 2026-06-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_add_notification_channels"
down_revision: Union[str, Sequence[str], None] = (
    "20260627_add_product_plan_version_history",
    "20260626_add_workflow_transition_specs",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_type", sa.String(32), nullable=False, index=True,
                  comment="通道类型: wecom / dingtalk"),
        sa.Column("name", sa.String(128), nullable=False,
                  comment="通道名称/备注"),
        sa.Column("webhook_url", sa.String(512), nullable=False,
                  comment="Webhook 机器人地址"),
        sa.Column("secret", sa.String(256), nullable=True, default="",
                  comment="签名密钥（钉钉必填，企微可选）"),
        sa.Column("daily_limit", sa.Integer(), nullable=False, default=1000,
                  comment="每日消息条数上限"),
        sa.Column("status", sa.String(16), nullable=False, default="active",
                  comment="运行状态: active / rate_limited / error"),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True,
                  comment="是否启用"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notification_channels")
