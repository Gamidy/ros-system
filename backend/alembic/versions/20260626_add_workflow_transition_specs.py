"""add_workflow_transition_specs — 创建流程转换规则表并插入种子数据

Revision ID: 20260626_add_workflow_transition_specs
Revises: 20260626_add_version_id_to_plan_subs
Create Date: 2026-06-26 18:35:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260626_add_workflow_transition_specs"
down_revision: Union[str, None] = "20260626_add_version_id_to_plan_subs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: CREATE TABLE workflow_transition_specs
    op.create_table(
        "workflow_transition_specs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("from_stage", sa.String(30), nullable=False, comment="源阶段 (ProductPlanStage 枚举值)"),
        sa.Column("to_stage", sa.String(30), nullable=False, comment="目标阶段 (ProductPlanStage 枚举值)"),
        sa.Column("required_fields", sa.Text(), nullable=True, comment="必填字段 JSON 数组"),
        sa.Column("required_condition", sa.Text(), nullable=True, comment="Python 表达式字符串条件"),
        sa.Column("required_label", sa.String(200), nullable=True, comment="条件描述（给前端展示）"),
        sa.Column("auto_advance", sa.Boolean(), default=False, comment="是否自动推进"),
        sa.Column("roles_allowed", sa.Text(), nullable=True, comment="允许推进的角色 JSON 数组"),
        sa.Column("sort_order", sa.Integer(), default=0, comment="排序"),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True, comment="所属组织ID"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), comment="创建时间"),
    )

    # Step 2: INSERT 种子数据（7条转换规则）
    op.execute(
        """
        INSERT INTO workflow_transition_specs
            (from_stage, to_stage, required_fields, required_condition, required_label,
             auto_advance, roles_allowed, sort_order, org_id)
        VALUES
            ('draft', 'competitor', '["name"]', NULL, '请填写策划名称',
             0, NULL, 10, NULL),
            ('competitor', 'definition', '["competitor_id","series","market"]', NULL, '请完成竞品分析并填写产品系列和目标市场',
             0, NULL, 20, NULL),
            ('definition', 'costing', '["cost_target"]', NULL, '请设定成本目标',
             0, NULL, 30, NULL),
            ('costing', 'tech_input', '["performance_target"]', NULL, '请填写技术指标',
             0, NULL, 40, NULL),
            ('tech_input', 'project_init', '["costs"]', NULL, '请维护成本明细',
             0, NULL, 50, NULL),
            ('project_init', 'approved', '["name"]', NULL, '请确认策划名称',
             0, NULL, 60, NULL),
            ('approved', 'released', '[]', NULL, '',
             0, NULL, 70, NULL)
        """
    )


def downgrade() -> None:
    op.drop_table("workflow_transition_specs")
