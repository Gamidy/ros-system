"""add unit_type column to competitor_models

Revision ID: 20260630_add_unit_type
Revises: 20260628_add_extra_fields_json
Create Date: 2026-06-30 10:00:00.000000
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260630_add_unit_type"
down_revision: str = "20260628_add_extra_fields_json"
branch_labels: Sequence[str] = None
depends_on: Sequence[str] = None


def upgrade():
    op.execute(
        "ALTER TABLE competitor_models "
        "ADD COLUMN unit_type VARCHAR(20) DEFAULT NULL "
        "COMMENT '单冷/冷暖（cooling_only/heat_pump）' "
        "AFTER factory_price"
    )


def downgrade():
    op.execute("ALTER TABLE competitor_models DROP COLUMN unit_type")
