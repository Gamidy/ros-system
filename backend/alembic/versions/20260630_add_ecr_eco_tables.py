"""add_ecr_eco_tables — ECR/ECO 工程变更控制模块 4张新表

1. ecr_requests       — 工程变更申请（ECR）
2. ecr_attachments    — ECR附件
3. ecos               — 工程变更指令（ECO）
4. eco_items          — ECO明细项

Revision ID: 20260630_add_ecr_eco_tables
Revises: 20260630_add_unit_type
Create Date: 2026-06-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON


revision: str = "20260630_add_ecr_eco_tables"
down_revision: Union[str, Sequence[str], None] = "20260630_add_unit_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. 工程变更申请(ECR) ──
    op.create_table(
        "ecr_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False, index=True, unique=True,
                  comment="ECR编号: ECR-YYYYMMDD-XXXX"),
        sa.Column("title", sa.String(200), nullable=False,
                  comment="变更标题"),
        sa.Column("ecr_type", sa.String(30), nullable=False,
                  comment="变更类型"),
        sa.Column("reason", sa.Text(), nullable=False,
                  comment="变更原因"),
        sa.Column("urgency", sa.String(20), nullable=False,
                  comment="紧急度"),
        sa.Column("affected_products", JSON(), nullable=True,
                  comment="影响产品JSON"),
        sa.Column("affected_documents", JSON(), nullable=True,
                  comment="影响文件JSON"),
        sa.Column("description", sa.Text(), nullable=True,
                  comment="详细描述"),
        sa.Column("status", sa.String(20), nullable=False,
                  comment="状态"),
        sa.Column("workflow_id", sa.Integer(), nullable=True,
                  comment="关联审批请求ID"),
        sa.Column("submitter_id", sa.Integer(), nullable=False,
                  comment="提交人"),
        sa.Column("submitter_name", sa.String(50), nullable=True,
                  comment="提交人姓名"),
        sa.Column("reviewer_id", sa.Integer(), nullable=True,
                  comment="审批人"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True,
                  comment="审批时间"),
        sa.Column("rejection_reason", sa.Text(), nullable=True,
                  comment="驳回原因"),
        sa.Column("org_id", sa.Integer(), nullable=True,
                  comment="所属组织ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now(),
                  comment="更新时间"),
        sa.ForeignKeyConstraint(["submitter_id"], ["users.id"],),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"],),
        sa.ForeignKeyConstraint(["workflow_id"], ["approval_requests.id"],),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"],),
        sa.PrimaryKeyConstraint("id"),
        comment="工程变更申请(ECR)",
    )

    # ── 2. ECR附件 ──
    op.create_table(
        "ecr_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ecr_id", sa.Integer(), nullable=False,
                  comment="关联ECR"),
        sa.Column("file_name", sa.String(255), nullable=False,
                  comment="文件名"),
        sa.Column("file_path", sa.String(500), nullable=False,
                  comment="文件路径"),
        sa.Column("file_type", sa.String(50), nullable=True,
                  comment="文件类型"),
        sa.Column("file_size", sa.Integer(), nullable=False, default=0,
                  comment="文件大小(字节)"),
        sa.Column("uploaded_by", sa.String(100), nullable=True,
                  comment="上传人"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.ForeignKeyConstraint(["ecr_id"], ["ecr_requests.id"],),
        sa.PrimaryKeyConstraint("id"),
        comment="ECR附件",
    )

    # ── 3. 工程变更指令(ECO) ──
    op.create_table(
        "ecos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False, index=True, unique=True,
                  comment="ECO编号: ECO-YYYYMMDD-XXXX"),
        sa.Column("ecr_id", sa.Integer(), nullable=True,
                  comment="来源ECR"),
        sa.Column("title", sa.String(200), nullable=False,
                  comment="变更标题"),
        sa.Column("change_summary", sa.Text(), nullable=False,
                  comment="变更摘要"),
        sa.Column("implementation_plan", sa.Text(), nullable=True,
                  comment="实施方案"),
        sa.Column("effective_date", sa.Date(), nullable=True,
                  comment="生效日期"),
        sa.Column("status", sa.String(20), nullable=False,
                  comment="状态"),
        sa.Column("created_by", sa.Integer(), nullable=False,
                  comment="创建人"),
        sa.Column("verified_by", sa.Integer(), nullable=True,
                  comment="验证人"),
        sa.Column("verified_at", sa.DateTime(), nullable=True,
                  comment="验证时间"),
        sa.Column("closed_by", sa.Integer(), nullable=True,
                  comment="关闭人"),
        sa.Column("closed_at", sa.DateTime(), nullable=True,
                  comment="关闭时间"),
        sa.Column("org_id", sa.Integer(), nullable=True,
                  comment="所属组织ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now(),
                  comment="更新时间"),
        sa.ForeignKeyConstraint(["ecr_id"], ["ecr_requests.id"],),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"],),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"],),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"],),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"],),
        sa.PrimaryKeyConstraint("id"),
        comment="工程变更指令(ECO)",
    )
    op.create_index("idx_ecos_ecr_id", "ecos", ["ecr_id"])

    # ── 4. ECO明细项 ──
    op.create_table(
        "eco_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("eco_id", sa.Integer(), nullable=False,
                  comment="关联ECO"),
        sa.Column("seq", sa.Integer(), nullable=False, default=0,
                  comment="序号"),
        sa.Column("change_type", sa.String(20), nullable=False,
                  comment="变更类型"),
        sa.Column("object_type", sa.String(20), nullable=False,
                  comment="对象类型"),
        sa.Column("object_id", sa.Integer(), nullable=True,
                  comment="对象ID"),
        sa.Column("object_code", sa.String(100), nullable=True,
                  comment="对象编码"),
        sa.Column("object_name", sa.String(200), nullable=True,
                  comment="对象名称"),
        sa.Column("old_value", sa.Text(), nullable=True,
                  comment="原值"),
        sa.Column("new_value", sa.Text(), nullable=True,
                  comment="新值"),
        sa.Column("description", sa.Text(), nullable=True,
                  comment="描述"),
        sa.Column("org_id", sa.Integer(), nullable=True,
                  comment="所属组织ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.ForeignKeyConstraint(["eco_id"], ["ecos.id"],),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"],),
        sa.PrimaryKeyConstraint("id"),
        comment="ECO明细项",
    )
    op.create_index("idx_eco_items_eco_id", "eco_items", ["eco_id"])


def downgrade() -> None:
    op.drop_table("eco_items")
    op.drop_table("ecos")
    op.drop_table("ecr_attachments")
    op.drop_table("ecr_requests")
