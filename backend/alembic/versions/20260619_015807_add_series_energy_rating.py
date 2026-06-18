"""add_series_energy_rating — 产品立项书Tab1新增系列名称/能效等级字段 + KB种子数据

Revision ID: 20260619_015807
Revises: 1e2a676b5556
Create Date: 2026-06-19 01:58:07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '20260619_015807'
down_revision: Union[str, None] = '1e2a676b5556'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════
# KB 种子数据
# ═══════════════════════════════════════════════════════════════

SERIES_SEEDS = [
    {"category": "series", "code": "J", "name": "J", "sort_order": 1},
    {"category": "series", "code": "K", "name": "K", "sort_order": 2},
    {"category": "series", "code": "L", "name": "L", "sort_order": 3},
    {"category": "series", "code": "M", "name": "M", "sort_order": 4},
    {"category": "series", "code": "N", "name": "N", "sort_order": 5},
    {"category": "series", "code": "P", "name": "P", "sort_order": 6},
    {"category": "series", "code": "R", "name": "R", "sort_order": 7},
    {"category": "series", "code": "S", "name": "S", "sort_order": 8},
    {"category": "series", "code": "T", "name": "T", "sort_order": 9},
]

ENERGY_RATING_SEEDS = [
    {"category": "energy_rating", "code": "5星", "name": "5星", "sort_order": 1},
    {"category": "energy_rating", "code": "4星", "name": "4星", "sort_order": 2},
    {"category": "energy_rating", "code": "3星", "name": "3星", "sort_order": 3},
    {"category": "energy_rating", "code": "2星", "name": "2星", "sort_order": 4},
    {"category": "energy_rating", "code": "1星", "name": "1星", "sort_order": 5},
]

knowledge_items = sa.table(
    "knowledge_items",
    sa.column("category", sa.String),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("sort_order", sa.Integer),
)


def upgrade() -> None:
    # ── 新增 projects 表字段 ──
    op.add_column("projects", sa.Column("series_name", sa.String(50), nullable=True, comment="系列名称（如 J/K/L/M）"))
    op.add_column("projects", sa.Column("energy_rating", sa.String(20), nullable=True, comment="能效等级（如 5星/3星/1星）"))

    # ── 插入 KB 种子数据（若不存在） ──
    conn = op.get_bind()

    for seed in SERIES_SEEDS:
        existing = conn.execute(
            sa.text("SELECT 1 FROM knowledge_items WHERE category=:cat AND code=:code"),
            {"cat": seed["category"], "code": seed["code"]},
        ).first()
        if not existing:
            op.bulk_insert(knowledge_items, [seed])

    for seed in ENERGY_RATING_SEEDS:
        existing = conn.execute(
            sa.text("SELECT 1 FROM knowledge_items WHERE category=:cat AND code=:code"),
            {"cat": seed["category"], "code": seed["code"]},
        ).first()
        if not existing:
            op.bulk_insert(knowledge_items, [seed])


def downgrade() -> None:
    op.drop_column("projects", "energy_rating")
    op.drop_column("projects", "series_name")

    # 不删除 KB 数据（避免误删）; 如需清理，管理员可在后台手动删除
