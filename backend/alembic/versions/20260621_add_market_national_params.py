"""add_market_national_params — markets表新增国家级参数 + 认证/压缩机关联表

Revision ID: 20260621_add_market_national_params
Revises: 20260619_015807
Create Date: 2026-06-21 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '20260621_add_market_national_params'
down_revision: Union[str, None] = '20260619_015807'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. markets 表新增国家级参数字段 ──
    op.add_column("markets", sa.Column("energy_standard_detail", sa.String(100), nullable=True,
                  comment="能效标准细分（如 2025新标准/MEPS等级）"))
    op.add_column("markets", sa.Column("national_standard", sa.String(100), nullable=True,
                  comment="国家标准编号，如 GB/T 7725"))
    op.add_column("markets", sa.Column("voltage_freq", sa.String(50), nullable=True,
                  comment="电压/频率，如 220V/50Hz"))
    op.add_column("markets", sa.Column("cooling_max_temp", sa.Float(), nullable=True,
                  comment="制冷最高环境温度 °C"))
    op.add_column("markets", sa.Column("heating_min_temp", sa.Float(), nullable=True,
                  comment="制热最低环境温度 °C"))
    op.add_column("markets", sa.Column("structure_type", sa.String(100), nullable=True,
                  comment="机型结构（分体壁挂/天花/风管/柜机）"))
    op.add_column("markets", sa.Column("main_selling_model", sa.String(200), nullable=True,
                  comment="主销机型描述"))
    op.add_column("markets", sa.Column("refrigerant", sa.String(50), nullable=True,
                  comment="主要制冷剂，如 R32/R410A/R290"))
    op.add_column("markets", sa.Column("refrigerant_charge", sa.Float(), nullable=True,
                  comment="标准制冷剂灌注量 g"))

    # ── 2. 新建市场认证要求表 ──
    op.create_table(
        "market_certifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market_code", sa.String(20), nullable=False, index=True,
                  comment="关联市场代码"),
        sa.Column("cert_type", sa.String(30), nullable=False,
                  comment="认证类型: safety/energy/emc/environmental"),
        sa.Column("cert_standard", sa.String(200), nullable=False,
                  comment="认证标准/要求"),
        sa.Column("description", sa.String(500), nullable=True,
                  comment="详细说明"),
        sa.Column("is_required", sa.String(5), nullable=True, server_default="true",
                  comment="是否强制"),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0",
                  comment="排序"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 3. 新建市场压缩机信息表 ──
    op.create_table(
        "market_compressors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market_code", sa.String(20), nullable=False, index=True,
                  comment="关联市场代码"),
        sa.Column("manufacturer", sa.String(100), nullable=False,
                  comment="压缩机制造商"),
        sa.Column("model", sa.String(100), nullable=True,
                  comment="压缩机型号"),
        sa.Column("capacity_range", sa.String(50), nullable=True,
                  comment="适用冷量段"),
        sa.Column("notes", sa.String(500), nullable=True,
                  comment="备注"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # 逆序操作
    op.drop_table("market_compressors")
    op.drop_table("market_certifications")
    op.drop_column("markets", "refrigerant_charge")
    op.drop_column("markets", "refrigerant")
    op.drop_column("markets", "main_selling_model")
    op.drop_column("markets", "structure_type")
    op.drop_column("markets", "heating_min_temp")
    op.drop_column("markets", "cooling_max_temp")
    op.drop_column("markets", "voltage_freq")
    op.drop_column("markets", "national_standard")
    op.drop_column("markets", "energy_standard_detail")
