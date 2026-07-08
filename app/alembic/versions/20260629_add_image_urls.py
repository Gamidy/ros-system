"""add image_urls column to competitor_models

Revision ID: 20260629_add_image_urls
Revises: 20260629_add_extra_fields
Create Date: 2026-06-29 10:00:00.000000
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260629_add_image_urls"
down_revision: str = "20260629_add_extra_fields"
branch_labels: Sequence[str] = None
depends_on: Sequence[str] = None


def upgrade():
    op.execute("ALTER TABLE competitor_models ADD COLUMN image_urls JSON DEFAULT NULL COMMENT '外观图片URL数组'")


def downgrade():
    op.execute("ALTER TABLE competitor_models DROP COLUMN image_urls")
