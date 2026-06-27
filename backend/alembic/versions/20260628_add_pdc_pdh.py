"""add_pdc_pdh — 竞品表追加 Pdesignc/Pdesignh 字段

欧盟能效标签要求：制冷设计负荷 Pdesignc、制热设计负荷 Pdesignh。

Revision ID: 20260628_add_pdc_pdh
Revises: 20260628_add_scop_heating_rating
Create Date: 2026-06-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_add_pdc_pdh"
down_revision: Union[str, Sequence[str], None] = "20260628_add_scop_heating_rating"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "competitor_models",
        sa.Column("pdc", sa.Float(), nullable=True, comment="制冷设计负荷 Pdesignc(kW)(欧盟)"),
    )
    op.add_column(
        "competitor_models",
        sa.Column("pdh", sa.Float(), nullable=True, comment="制热设计负荷 Pdesignh(kW)(欧盟)"),
    )


def downgrade() -> None:
    op.drop_column("competitor_models", "pdh")
    op.drop_column("competitor_models", "pdc")
