"""add_version_id_to_plan_subs — 给4个子表添加 version_id 版本号字段

Revision ID: 20260626_add_version_id_to_plan_subs
Revises: 20260626_add_product_plan_project_links
Create Date: 2026-06-26 18:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260626_add_version_id_to_plan_subs"
down_revision: Union[str, None] = "20260626_add_product_plan_project_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in [
        "product_plan_initiations",
        "product_plan_markets",
        "product_plan_tech_specs",
        "product_plan_teams",
    ]:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column("version_id", sa.Integer(), server_default="1", nullable=False, comment="版本号, 每次更新+1")
            )


def downgrade() -> None:
    for table in [
        "product_plan_initiations",
        "product_plan_markets",
        "product_plan_tech_specs",
        "product_plan_teams",
    ]:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("version_id")
