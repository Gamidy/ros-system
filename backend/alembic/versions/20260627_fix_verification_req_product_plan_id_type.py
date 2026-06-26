"""fix_verification_req_product_plan_id_type — verification_requirements.product_plan_id Integer→String(36)

product_plans.id 是 VARCHAR(36)，但 verification_requirements.product_plan_id 还遗留为 INTEGER。
需要将列类型改为 VARCHAR(36) 以匹配 FK 目标并支持 UUID 格式的 plan_id。

Revision ID: 20260627_fix_verification_req_product_plan_id_type
Revises: 20260626_add_versioned_fields_to_product_plan_links
Create Date: 2026-06-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_fix_verification_req_product_plan_id_type"
down_revision: Union[str, None] = "20260626_add_versioned_fields_to_product_plan_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 不支持 ALTER COLUMN TYPE，必须用 batch_alter_table 重建表
    with op.batch_alter_table("verification_requirements") as batch_op:
        batch_op.alter_column(
            "product_plan_id",
            type_=sa.String(36),
            nullable=True,
            existing_type=sa.Integer(),
            existing_nullable=True,
        )


def downgrade() -> None:
    # 回退：改回 INTEGER
    with op.batch_alter_table("verification_requirements") as batch_op:
        batch_op.alter_column(
            "product_plan_id",
            type_=sa.Integer(),
            nullable=True,
            existing_type=sa.String(36),
            existing_nullable=True,
        )
