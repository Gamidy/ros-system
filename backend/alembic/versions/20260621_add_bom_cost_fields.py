"""add_bom_cost_fields — BOMItem新增成本字段 unit_price/amount/unit

Revision ID: 20260621_bom_cost
Revises: 20260619_015807
Create Date: 2026-06-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '20260621_bom_cost'
down_revision: Union[str, None] = '20260619_015807'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 新增 bom_items 表成本字段 ──
    op.add_column("bom_items", sa.Column("unit", sa.String(20), nullable=True, server_default="个", comment="单位"))
    op.add_column("bom_items", sa.Column("unit_price", sa.Float, nullable=True, server_default="0", comment="单价（元）"))
    op.add_column("bom_items", sa.Column("amount", sa.Float, nullable=True, server_default="1", comment="用量/系数"))

    # ── 为现有BOM数据设置参考价格 ──
    # BOM-ROS-R32-12000-001 的17个节点按层级定价
    conn = op.get_bind()

    # 使用 part_no 精确匹配更新
    price_updates = [
        # (part_no, unit_price, amount, unit)
        # L1 整机
        ("ROS-R32-12000-001", 0, 1, "台"),
        # L2 内外机
        ("IDU-R32-12000-A", 0, 1, "台"),
        ("ODU-R32-12000-A", 0, 1, "台"),
        # L3 总成
        ("EVAP-ASSY-12000", 0, 1, "套"),
        ("COND-ASSY-12000", 0, 1, "套"),
        ("ELEC-CTRL-BOX", 85.00, 1, "套"),
        ("FAN-MOTOR-ASSY", 45.00, 1, "套"),
        # L4 组件
        ("EVAP-COIL-12000", 120.00, 1, "套"),
        ("FILTER-ASSY-12000", 8.00, 1, "套"),
        ("DRAIN-PAN-ASSY", 12.00, 1, "套"),
        ("COND-COIL-12000", 150.00, 1, "套"),
        ("COMPRESSOR-R32-12000", 280.00, 1, "个"),
        ("PCB-MAIN-V1", 65.00, 1, "块"),
        ("PCB-DISPLAY-V1", 22.00, 1, "块"),
        ("WIRING-HARNESS", 18.00, 1, "套"),
        # L5 子件
        ("FAN-BLADE-12000", 15.00, 1, "个"),
        ("MOTOR-DC-30W", 35.00, 1, "个"),
    ]

    for part_no, unit_price, amount, unit in price_updates:
        conn.execute(
            sa.text(
                "UPDATE bom_items SET unit_price=:up, amount=:amt, unit=:u WHERE part_no=:pn"
            ),
            {"up": unit_price, "amt": amount, "u": unit, "pn": part_no},
        )

    # 为没有匹配到的条目设置默认值
    conn.execute(
        sa.text("UPDATE bom_items SET unit='个' WHERE unit IS NULL")
    )
    conn.execute(
        sa.text("UPDATE bom_items SET unit_price=0 WHERE unit_price IS NULL")
    )
    conn.execute(
        sa.text("UPDATE bom_items SET amount=1 WHERE amount IS NULL")
    )


def downgrade() -> None:
    op.drop_column("bom_items", "amount")
    op.drop_column("bom_items", "unit_price")
    op.drop_column("bom_items", "unit")
