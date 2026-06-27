"""add_market_param_configs — 市场参数配置表

产品经理可自行配置每个市场有哪些专有参数（如EU的SCOP/PDC/PDH、
越南的CSPF、加纳的AEER），配置后前端动态渲染对应表单字段。
值存储在 competitor_models.extra_fields JSON列中。

Revision ID: 20260628_add_market_param_configs
Revises: 20260628_add_pdc_pdh
Create Date: 2026-06-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON

revision: str = "20260628_add_market_param_configs"
down_revision: Union[str, Sequence[str], None] = "20260628_add_pdc_pdh"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_param_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("market_code", sa.String(20), sa.ForeignKey("markets.code", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("param_key", sa.String(50), nullable=False, comment="参数键名，存于 extra_fields JSON"),
        sa.Column("param_label", sa.String(100), nullable=False, comment="显示标签，如 AEER/CSPF/SCOP"),
        sa.Column("param_unit", sa.String(50), nullable=True, comment="单位，如 W/W/kW/dB"),
        sa.Column("data_type", sa.String(20), nullable=False, server_default=sa.text("'float'"),
                  comment="数据类型: float/int/string/select"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="排序"),
        sa.Column("is_required", sa.String(5), nullable=False, server_default=sa.text("'false'")),
        sa.Column("options", JSON, nullable=True, comment="当 data_type=select 时的选项列表"),
        sa.Column("is_active", sa.String(5), nullable=False, server_default=sa.text("'true'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("market_code", "param_key", name="uq_market_param"),
    )

    # ── 预置已知市场的参数配置 ──────────────────────────────────────

    # 欧盟：SCOP + PDC + PDH + 声功率 + 制热能效等级
    eu_params = [
        ("scop", "SCOP", "W/W", "float", 10, "true"),
        ("pdc", "Pdesignc", "kW", "float", 20, "true"),
        ("pdh", "Pdesignh", "kW", "float", 20, "false"),
        ("noise_indoor_power_db", "室内噪音(声功率)", "dB", "float", 30, "false"),
        ("noise_outdoor_power_db", "室外噪音(声功率)", "dB", "float", 31, "false"),
        ("heating_energy_rating", "制热能效等级", "", "string", 40, "false"),
    ]
    for key, label, unit, dtype, order, required in eu_params:
        op.execute(
            sa.text(
                """INSERT INTO market_param_configs 
                   (market_code, param_key, param_label, param_unit, data_type, sort_order, is_required)
                   SELECT 'EU', :key, :label, :unit, :dtype, :order, :required
                   WHERE EXISTS (SELECT 1 FROM markets WHERE name = '欧盟')
                   AND NOT EXISTS (
                       SELECT 1 FROM market_param_configs 
                       WHERE market_code = 'EU' AND param_key = :key
                   )"""
            ).bindparams(key=key, label=label, unit=unit, dtype=dtype, order=order, required=required)
        )

    # 加纳：AEER
    op.execute(
        sa.text(
            """INSERT INTO market_param_configs 
               (market_code, param_key, param_label, param_unit, data_type, sort_order, is_required)
               SELECT 'GH', 'aeer', 'AEER', 'W/W', 'float', 10, 'true'
               WHERE EXISTS (SELECT 1 FROM markets WHERE name = '加纳')
               AND NOT EXISTS (
                   SELECT 1 FROM market_param_configs 
                   WHERE market_code = 'GH' AND param_key = 'aeer'
               )"""
        )
    )

    # 澳大利亚：AEER
    op.execute(
        sa.text(
            """INSERT INTO market_param_configs 
               (market_code, param_key, param_label, param_unit, data_type, sort_order, is_required)
               SELECT 'AU', 'aeer', 'AEER', 'W/W', 'float', 10, 'true'
               WHERE EXISTS (SELECT 1 FROM markets WHERE name = '澳大利亚')
               AND NOT EXISTS (
                   SELECT 1 FROM market_param_configs 
                   WHERE market_code = 'AU' AND param_key = 'aeer'
               )"""
        )
    )

    # 越南：CSPF（已有 cspf 列，但为了兼容统一也配进去）
    op.execute(
        sa.text(
            """INSERT INTO market_param_configs 
               (market_code, param_key, param_label, param_unit, data_type, sort_order, is_required)
               SELECT 'VN', 'cspf', 'CSPF', 'W/W', 'float', 10, 'true'
               WHERE EXISTS (SELECT 1 FROM markets WHERE name = '越南')
               AND NOT EXISTS (
                   SELECT 1 FROM market_param_configs 
                   WHERE market_code = 'VN' AND param_key = 'cspf'
               )"""
        )
    )


def downgrade() -> None:
    op.drop_table("market_param_configs")
