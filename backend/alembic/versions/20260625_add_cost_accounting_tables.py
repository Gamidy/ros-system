"""add_cost_accounting_tables — 成本核算系统7张核心表

Revision ID: 20260625_add_cost_accounting_tables
Revises: 20260622_add_proposal_parallel_reviewers
Create Date: 2026-06-25 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "20260625_add_cost_accounting_tables"
down_revision: Union[str, None] = "20260622_add_proposal_parallel_reviewers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. 核算期间 ──
    op.create_table(
        "cost_accounting_periods",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_name", sa.String(50), nullable=False, comment="期间名称"),
        sa.Column("start_date", sa.String(10), nullable=False, comment="开始日期"),
        sa.Column("end_date", sa.String(10), nullable=False, comment="结束日期"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", comment="状态"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="所属组织ID"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ca_period_org", "cost_accounting_periods", ["org_id"])
    op.create_index("idx_ca_period_status", "cost_accounting_periods", ["status"])

    # ── 2. 成本核算单 ──
    op.create_table(
        "cost_accounting_sheets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sheet_no", sa.String(50), nullable=False, comment="核算单编号"),
        sa.Column("product_plan_id", sa.String(36), sa.ForeignKey("product_plans.id"), nullable=False, comment="关联策划"),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("cost_accounting_periods.id"), nullable=False, comment="期间"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", comment="状态"),

        sa.Column("material_cost_actual", sa.Float(), server_default="0", comment="物料成本实际"),
        sa.Column("material_cost_target", sa.Float(), server_default="0", comment="物料成本目标"),

        sa.Column("labor_cost_actual", sa.Float(), server_default="0", comment="人工成本实际"),
        sa.Column("labor_cost_target", sa.Float(), server_default="0", comment="人工成本目标"),

        sa.Column("overhead_cost_actual", sa.Float(), server_default="0", comment="制造费用实际"),
        sa.Column("overhead_cost_target", sa.Float(), server_default="0", comment="制造费用目标"),

        sa.Column("total_cost_actual", sa.Float(), server_default="0", comment="总成本实际"),
        sa.Column("total_cost_target", sa.Float(), server_default="0", comment="总成本目标"),
        sa.Column("variance_amount", sa.Float(), server_default="0", comment="差异额"),
        sa.Column("variance_pct", sa.Float(), server_default="0", comment="差异率%"),

        sa.Column("currency", sa.String(10), server_default="CNY", comment="币种"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="组织"),
        sa.Column("created_by", sa.String(50), nullable=True, comment="创建者"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sheet_no"),
    )
    op.create_index("idx_ca_sheet_no", "cost_accounting_sheets", ["sheet_no"])
    op.create_index("idx_ca_sheet_plan", "cost_accounting_sheets", ["product_plan_id"])
    op.create_index("idx_ca_sheet_period", "cost_accounting_sheets", ["period_id"])
    op.create_index("idx_ca_sheet_org", "cost_accounting_sheets", ["org_id"])

    # ── 3. 核算单项明细 ──
    op.create_table(
        "cost_accounting_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sheet_id", sa.Integer(), sa.ForeignKey("cost_accounting_sheets.id"), nullable=False, comment="核算单"),
        sa.Column("cost_category", sa.String(20), nullable=False, comment="类别: material/labor/overhead"),
        sa.Column("item_name", sa.String(100), nullable=False, comment="成本项名"),
        sa.Column("target_amount", sa.Float(), server_default="0", comment="目标金额"),
        sa.Column("actual_amount", sa.Float(), server_default="0", comment="实际金额"),
        sa.Column("variance", sa.Float(), server_default="0", comment="差异"),
        sa.Column("variance_pct", sa.Float(), server_default="0", comment="差异率%"),
        sa.Column("source_type", sa.String(50), nullable=True, comment="来源类型"),
        sa.Column("source_id", sa.Integer(), nullable=True, comment="来源ID"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="组织"),
        sa.Column("remark", sa.String(500), nullable=True, comment="备注"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ca_item_sheet", "cost_accounting_items", ["sheet_id"])
    op.create_index("idx_ca_item_category", "cost_accounting_items", ["cost_category"])

    # ── 4. 工时费率配置 ──
    op.create_table(
        "labor_rate_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("operation_code", sa.String(50), nullable=False, comment="工序编码"),
        sa.Column("operation_name", sa.String(100), nullable=False, comment="工序名称"),
        sa.Column("hourly_rate", sa.Float(), nullable=False, comment="费率(元/小时)"),
        sa.Column("unit", sa.String(10), server_default="hour", comment="单位"),
        sa.Column("status", sa.String(10), server_default="active", comment="状态"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="组织"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_lr_org", "labor_rate_configs", ["org_id"])
    op.create_index("idx_lr_code", "labor_rate_configs", ["operation_code"])

    # ── 5. 产品人工成本 ──
    op.create_table(
        "product_labor_costs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_plan_id", sa.String(36), sa.ForeignKey("product_plans.id"), nullable=False, comment="策划"),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("cost_accounting_periods.id"), nullable=False, comment="期间"),
        sa.Column("operation_code", sa.String(50), nullable=False, comment="工序编码"),
        sa.Column("operation_name", sa.String(100), nullable=False, comment="工序名称"),
        sa.Column("labor_hours", sa.Float(), nullable=False, comment="工时数"),
        sa.Column("hourly_rate", sa.Float(), nullable=False, comment="费率快照"),
        sa.Column("total_amount", sa.Float(), server_default="0", comment="金额"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="组织"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_plc_plan", "product_labor_costs", ["product_plan_id"])
    op.create_index("idx_plc_period", "product_labor_costs", ["period_id"])
    op.create_index("idx_plc_org", "product_labor_costs", ["org_id"])

    # ── 6. 间接费分摊规则 ──
    op.create_table(
        "overhead_allocation_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_name", sa.String(100), nullable=False, comment="规则名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="说明"),
        sa.Column("allocation_base", sa.String(30), nullable=False, comment="分摊基准"),
        sa.Column("allocation_rate", sa.Float(), nullable=False, comment="分摊比例%"),
        sa.Column("is_active", sa.Integer(), server_default="1", comment="启用"),
        sa.Column("priority", sa.Integer(), server_default="0", comment="优先级"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="组织"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_oar_org", "overhead_allocation_rules", ["org_id"])
    op.create_index("idx_oar_active", "overhead_allocation_rules", ["is_active"])

    # ── 7. 产品间接费分摊结果 ──
    op.create_table(
        "product_overhead_costs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_plan_id", sa.String(36), sa.ForeignKey("product_plans.id"), nullable=False, comment="策划"),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("cost_accounting_periods.id"), nullable=False, comment="期间"),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("overhead_allocation_rules.id"), nullable=False, comment="规则"),
        sa.Column("base_amount", sa.Float(), server_default="0", comment="分摊基数"),
        sa.Column("allocation_rate", sa.Float(), server_default="0", comment="快照分摊率"),
        sa.Column("allocation_amount", sa.Float(), server_default="0", comment="分摊金额"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="组织"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_poc_plan", "product_overhead_costs", ["product_plan_id"])
    op.create_index("idx_poc_period", "product_overhead_costs", ["period_id"])
    op.create_index("idx_poc_rule", "product_overhead_costs", ["rule_id"])
    op.create_index("idx_poc_org", "product_overhead_costs", ["org_id"])


def downgrade() -> None:
    op.drop_table("product_overhead_costs")
    op.drop_table("overhead_allocation_rules")
    op.drop_table("product_labor_costs")
    op.drop_table("labor_rate_configs")
    op.drop_table("cost_accounting_items")
    op.drop_table("cost_accounting_sheets")
    op.drop_table("cost_accounting_periods")
