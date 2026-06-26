"""add_versioned_fields_to_product_plan_links — 给 product_plan_project_links 表加版本号/方案分组字段

Revision ID: 20260626_add_versioned_fields_to_product_plan_links
Revises: 20260626_add_product_plan_project_links
Create Date: 2026-06-26 18:50:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260626_add_versioned_fields_to_product_plan_links"
down_revision: Union[str, None] = "20260626_add_product_plan_project_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("product_plan_project_links") as batch_op:
        batch_op.add_column(
            sa.Column("version_major", sa.Integer(), server_default="1", nullable=False, comment="主版本号")
        )
        batch_op.add_column(
            sa.Column("version_minor", sa.Integer(), server_default="0", nullable=False, comment="次版本号")
        )
        batch_op.add_column(
            sa.Column("snapshot_schema_version", sa.Integer(), server_default="1", nullable=False, comment="快照数据schema版本")
        )
        batch_op.add_column(
            sa.Column("scenario_group_id", sa.String(36), nullable=True, comment="方案分组ID(AB评估用)")
        )


def downgrade() -> None:
    with op.batch_alter_table("product_plan_project_links") as batch_op:
        batch_op.drop_column("version_major")
        batch_op.drop_column("version_minor")
        batch_op.drop_column("snapshot_schema_version")
        batch_op.drop_column("scenario_group_id")
