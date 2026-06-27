"""add_scop_heating_rating — 竞品表追加 SCOP 和制热能效等级字段

欧盟市场的竞品需要记录制热季节能效 SCOP 和制热能效等级。

Revision ID: 20260628_add_scop_heating_rating
Revises: 20260628_add_competitor_crawl_tables
Create Date: 2026-06-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_add_scop_heating_rating"
down_revision: Union[str, Sequence[str], None] = "20260628_add_competitor_crawl_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "competitor_models",
        sa.Column("scop", sa.Float(), nullable=True, comment="SCOP制热季节能效(欧盟)"),
    )
    op.add_column(
        "competitor_models",
        sa.Column(
            "heating_energy_rating",
            sa.String(40),
            nullable=True,
            comment="制热能效等级",
        ),
    )
    op.add_column(
        "competitor_models",
        sa.Column(
            "noise_indoor_power_db",
            sa.Float(),
            nullable=True,
            comment="室内噪音声功率级(dB)(欧盟)",
        ),
    )
    op.add_column(
        "competitor_models",
        sa.Column(
            "noise_outdoor_power_db",
            sa.Float(),
            nullable=True,
            comment="室外噪音声功率级(dB)(欧盟)",
        ),
    )


def downgrade() -> None:
    op.drop_column("competitor_models", "noise_outdoor_power_db")
    op.drop_column("competitor_models", "noise_indoor_power_db")
    op.drop_column("competitor_models", "heating_energy_rating")
    op.drop_column("competitor_models", "scop")
