"""add_product_plan_version_history — 添加策划版本号 + 版本历史表

1. product_plans 表新增 version 列 (INTEGER NOT NULL DEFAULT 1)
2. 创建 product_plan_histories 表

Revision ID: 20260627_add_product_plan_version_history
Revises: 20260627_fix_verification_req_product_plan_id_type
Create Date: 2026-06-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_add_product_plan_version_history"
down_revision: Union[str, None] = "20260627_fix_verification_req_product_plan_id_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 1. product_plans 加 version 列 ===
    with op.batch_alter_table("product_plans") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )

    # === 2. 创建 product_plan_histories 表 ===
    op.create_table(
        "product_plan_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_plan_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("changed_by", sa.String(50), nullable=True),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_plan_id"],
            ["product_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_product_plan_histories_product_plan_id"),
        "product_plan_histories",
        ["product_plan_id"],
    )


def downgrade() -> None:
    # 删除索引 + 表
    op.drop_index(
        op.f("ix_product_plan_histories_product_plan_id"),
        table_name="product_plan_histories",
    )
    op.drop_table("product_plan_histories")

    # 移除 version 列
    with op.batch_alter_table("product_plans") as batch_op:
        batch_op.drop_column("version")
