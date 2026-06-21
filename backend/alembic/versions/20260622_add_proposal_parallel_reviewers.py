"""add_proposal_parallel_reviewers — 并行审批人独立表（替代JSON列，解决竞态条件）

Revision ID: 20260622_add_proposal_parallel_reviewers
Revises: 20260621_add_market_national_params
Create Date: 2026-06-22 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '20260622_add_proposal_parallel_reviewers'
down_revision: Union[str, None] = '20260621_add_market_national_params'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. 创建并行审批人独立表 ──
    op.create_table(
        "proposal_parallel_reviewers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("approval_id", sa.Integer(), nullable=False, index=True,
                  comment="关联 proposal_approvals.id"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="审批人 user_id"),
        sa.Column("username", sa.String(100), nullable=True, comment="审批人用户名"),
        sa.Column("role", sa.String(50), nullable=True, comment="审批角色"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True, comment="审批意见"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="审批时间"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 2. 从旧 JSON 列回填数据 ──
    # 使用 raw SQL 读取 JSON 并插入新表
    conn = op.get_bind()

    # 读取所有有 parallel_reviewers 数据的审批记录
    rows = conn.execute(
        sa.text(
            "SELECT id, parallel_reviewers FROM proposal_approvals "
            "WHERE parallel_reviewers IS NOT NULL AND parallel_reviewers != 'null'"
        )
    ).fetchall()

    for row in rows:
        approval_id, reviewers_json = row
        if not reviewers_json:
            continue
        # 兼容 MySQL JSON 类型和 SQLite TEXT 类型
        if isinstance(reviewers_json, str):
            import json
            try:
                reviewers = json.loads(reviewers_json)
            except (json.JSONDecodeError, TypeError):
                continue
        else:
            reviewers = reviewers_json  # MySQL JSON type

        for r in reviewers:
            if isinstance(r, dict):
                reviewed_at_val = r.get("reviewed_at")
                if reviewed_at_val and isinstance(reviewed_at_val, str) and reviewed_at_val.lower() != "none" and reviewed_at_val != "null":
                    reviewed_at_val = reviewed_at_val[:19]  # truncate to YYYY-MM-DDTHH:MM:SS
                else:
                    reviewed_at_val = None

                conn.execute(
                    sa.text(
                        "INSERT INTO proposal_parallel_reviewers "
                        "(approval_id, user_id, username, role, status, reason, reviewed_at) "
                        "VALUES (:approval_id, :user_id, :username, :role, :status, :reason, :reviewed_at)"
                    ),
                    {
                        "approval_id": approval_id,
                        "user_id": r.get("user_id"),
                        "username": r.get("username", ""),
                        "role": r.get("role", ""),
                        "status": r.get("status", "pending"),
                        "reason": r.get("reason", ""),
                        "reviewed_at": reviewed_at_val,
                    }
                )


def downgrade() -> None:
    op.drop_table("proposal_parallel_reviewers")
