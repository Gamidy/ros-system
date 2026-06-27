"""rebuild_user_notification_prefs — 重建用户通知偏好表为新 schema

旧表结构 (channel + event_types JSON) → 新表结构 (event_type + channel_type 独立列)

Revision ID: 20260627_rebuild_user_notification_prefs
Revises: 20260627_add_notification_channels
Create Date: 2026-06-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "20260627_rebuild_user_notification_prefs"
down_revision: Union[str, Sequence[str], None] = "20260627_add_notification_channels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先删除旧表（含旧唯一约束）
    op.drop_table("user_notification_prefs")

    # 重建新表
    op.create_table(
        "user_notification_prefs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True,
                  comment="用户ID"),
        sa.Column("event_type", sa.String(32), nullable=False,
                  comment="事件类型: approval_request / plan_submitted / review_due / alert"),
        sa.Column("channel_type", sa.String(32), nullable=False,
                  comment="推送渠道: wecom / dingtalk / email / websocket"),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True,
                  comment="是否启用该事件-渠道推送"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="更新时间"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "event_type", "channel_type",
            name="uq_user_event_channel",
        ),
    )


def downgrade() -> None:
    # 回退：删除新表，重建旧表结构
    op.drop_table("user_notification_prefs")

    op.create_table(
        "user_notification_prefs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True,
                  comment="用户ID"),
        sa.Column("channel", sa.String(32), nullable=False, default="all",
                  comment="通知通道: wecom / dingtalk / all"),
        sa.Column("event_types", sa.JSON(), nullable=False,
                  comment="感兴趣的事件类型列表"),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True,
                  comment="是否启用该通道的推送"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="更新时间"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "channel", name="uq_user_channel"),
    )
