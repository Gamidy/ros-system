"""add_product_plan_project_links — ProductPlan↔Project 解耦中间表

Step 1: CREATE TABLE product_plan_project_links
Step 2: 迁移存量 project_id 数据为 primary link
Step 3: DROP COLUMN product_plans.project_id

Revision ID: 20260626_add_product_plan_project_links
Revises: 20260625_add_cost_accounting_tables
Create Date: 2026-06-26 18:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "20260626_add_product_plan_project_links"
down_revision: Union[str, None] = "20260625_add_cost_accounting_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: 建新表
    op.create_table(
        "product_plan_project_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_plan_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(20), server_default="primary", nullable=False),
        sa.Column("snapshot_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_plan_id"], ["product_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ppl_product_plan_id", "product_plan_project_links", ["product_plan_id"])
    op.create_index("ix_ppl_project_id", "product_plan_project_links", ["project_id"])

    # Step 2: 迁移存量数据
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO product_plan_project_links (product_plan_id, project_id, link_type) "
            "SELECT id, project_id, 'primary' FROM product_plans WHERE project_id IS NOT NULL"
        )
    )

    # Step 3: 删旧列（先删FK约束再删列 — MariaDB需要）
    conn = op.get_bind()
    if conn.dialect.name == "mysql":
        # MariaDB: 先查找FK名再删除
        r = conn.execute(
            sa.text(
                "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'product_plans' "
                "AND COLUMN_NAME = 'project_id' AND REFERENCED_TABLE_NAME IS NOT NULL LIMIT 1"
            )
        )
        fk_row = r.fetchone()
        if fk_row:
            conn.execute(sa.text(f"ALTER TABLE product_plans DROP FOREIGN KEY {fk_row[0]}"))
        r2 = conn.execute(
            sa.text(
                "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'product_plans' "
                "AND COLUMN_NAME = 'project_id' LIMIT 1"
            )
        )
        idx_row = r2.fetchone()
        if idx_row:
            conn.execute(sa.text(f"ALTER TABLE product_plans DROP INDEX {idx_row[0]}"))
    with op.batch_alter_table("product_plans") as batch_op:
        batch_op.drop_column("project_id")


def downgrade() -> None:
    # 反向：恢复 project_id 列 + 从 links 回填 + 删 links 表
    with op.batch_alter_table("product_plans") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True))

    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        conn.execute(
            sa.text(
                "UPDATE product_plans SET project_id = "
                "(SELECT project_id FROM product_plan_project_links "
                "WHERE product_plan_project_links.product_plan_id = product_plans.id AND link_type = 'primary' LIMIT 1)"
            )
        )
    else:
        conn.execute(
            sa.text(
                "UPDATE product_plans p "
                "JOIN product_plan_project_links l ON l.product_plan_id = p.id AND l.link_type = 'primary' "
                "SET p.project_id = l.project_id"
            )
        )

    op.drop_table("product_plan_project_links")
