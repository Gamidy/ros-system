"""add_extra_fields_json — 竞品表用 JSON 替代欧盟专有硬编码列

EU专有参数（scop/heating_energy_rating/pdc/pdh/noise_indoor_power_db/
noise_outdoor_power_db）从独立列迁移到 extra_fields JSON列，
后续新增欧盟参数无需改表结构。

Revision ID: 20260628_add_extra_fields_json
Revises: 20260628_add_market_param_configs
Create Date: 2026-06-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON

revision: str = "20260628_add_extra_fields_json"
down_revision: Union[str, Sequence[str], None] = "20260628_add_market_param_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 添加 extra_fields JSON 列
    op.add_column(
        "competitor_models",
        sa.Column("extra_fields", JSON, nullable=True, comment="扩展参数(JSON)，如欧盟SCOP/PDC/PDH/声功率等"),
    )

    # 2. 迁移已有欧盟数据到 extra_fields
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, scop, heating_energy_rating, pdc, pdh, "
            "noise_indoor_power_db, noise_outdoor_power_db "
            "FROM competitor_models "
            "WHERE market = '欧盟' "
            "AND (scop IS NOT NULL OR heating_energy_rating IS NOT NULL "
            "OR pdc IS NOT NULL OR pdh IS NOT NULL "
            "OR noise_indoor_power_db IS NOT NULL OR noise_outdoor_power_db IS NOT NULL)"
        )
    ).fetchall()

    for row in rows:
        extra = {}
        if row.scop is not None:
            extra["scop"] = float(row.scop)
        if row.heating_energy_rating is not None:
            extra["heating_energy_rating"] = row.heating_energy_rating
        if row.pdc is not None:
            extra["pdc"] = float(row.pdc)
        if row.pdh is not None:
            extra["pdh"] = float(row.pdh)
        if row.noise_indoor_power_db is not None:
            extra["noise_indoor_power_db"] = float(row.noise_indoor_power_db)
        if row.noise_outdoor_power_db is not None:
            extra["noise_outdoor_power_db"] = float(row.noise_outdoor_power_db)

        if extra:
            import json
            bind.execute(
                sa.text(
                    "UPDATE competitor_models SET extra_fields = :extra WHERE id = :id"
                ),
                {"extra": json.dumps(extra, ensure_ascii=False), "id": row.id},
            )

    # 3. 删除旧列
    op.drop_column("competitor_models", "noise_outdoor_power_db")
    op.drop_column("competitor_models", "noise_indoor_power_db")
    op.drop_column("competitor_models", "pdh")
    op.drop_column("competitor_models", "pdc")
    op.drop_column("competitor_models", "heating_energy_rating")
    op.drop_column("competitor_models", "scop")


def downgrade() -> None:
    # 恢复旧列
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
        sa.Column("pdc", sa.Float(), nullable=True, comment="制冷设计负荷 Pdesignc(kW)(欧盟)"),
    )
    op.add_column(
        "competitor_models",
        sa.Column("pdh", sa.Float(), nullable=True, comment="制热设计负荷 Pdesignh(kW)(欧盟)"),
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

    # 从 extra_fields 恢复数据
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, extra_fields FROM competitor_models "
            "WHERE extra_fields IS NOT NULL AND extra_fields != '{}'"
        )
    ).fetchall()

    for row in rows:
        import json
        try:
            extra = json.loads(row.extra_fields) if isinstance(row.extra_fields, str) else (row.extra_fields or {})
        except (json.JSONDecodeError, TypeError):
            extra = {}

        updates = {}
        for col, key in [
            ("scop", "scop"),
            ("heating_energy_rating", "heating_energy_rating"),
            ("pdc", "pdc"),
            ("pdh", "pdh"),
            ("noise_indoor_power_db", "noise_indoor_power_db"),
            ("noise_outdoor_power_db", "noise_outdoor_power_db"),
        ]:
            if key in extra:
                updates[col] = extra[key]

        if updates:
            set_clause = ", ".join(f"{col} = :{col}" for col in updates)
            updates["id"] = row.id
            bind.execute(
                sa.text(f"UPDATE competitor_models SET {set_clause} WHERE id = :id"),
                updates,
            )

    # 删除 extra_fields 列
    op.drop_column("competitor_models", "extra_fields")
