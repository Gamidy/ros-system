"""add_competitor_crawl_tables — 竞品自动采集相关表

Stage 1 of 7 — Automated Competitor Collection System.
1. 创建 competitor_crawls 表（爬取日志）
2. 创建 competitor_search_terms 表（搜索词配置）
3. competitor_models 追加 source 和 source_url 字段

Revision ID: 20260628_add_competitor_crawl_tables
Revises: 20260627_rebuild_user_notification_prefs
Create Date: 2026-06-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_add_competitor_crawl_tables"
down_revision: Union[str, Sequence[str], None] = "20260627_rebuild_user_notification_prefs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. 竞品爬取日志表 ──
    op.create_table(
        "competitor_crawls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market_code", sa.String(20), nullable=False, index=True,
                  comment="目标市场代码: VN, US, SA..."),
        sa.Column("brand", sa.String(80), nullable=False, index=True,
                  comment="品牌: AUX / TCL"),
        sa.Column("started_at", sa.DateTime(), nullable=False,
                  comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(), nullable=True,
                  comment="结束时间"),
        sa.Column("status", sa.String(20), nullable=False, default="running",
                  comment="状态: running|success|partial|failed"),
        sa.Column("query_count", sa.Integer(), nullable=False, default=0,
                  comment="发起的搜索请求数"),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, default=0,
                  comment="成功抓取的页面数"),
        sa.Column("total_found", sa.Integer(), nullable=False, default=0,
                  comment="本次发现的总条目数"),
        sa.Column("new_added", sa.Integer(), nullable=False, default=0,
                  comment="新增入库数"),
        sa.Column("updated", sa.Integer(), nullable=False, default=0,
                  comment="更新数"),
        sa.Column("skipped", sa.Integer(), nullable=False, default=0,
                  comment="跳过数"),
        sa.Column("draft_count", sa.Integer(), nullable=False, default=0,
                  comment="标记为 draft 待审数"),
        sa.Column("error_message", sa.Text(), nullable=True,
                  comment="失败时的错误详情"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="竞品爬取任务日志",
    )
    # 复合索引: 市场+品牌 联合查询
    op.create_index("idx_crawl_market_brand", "competitor_crawls",
                    ["market_code", "brand"])

    # ── 2. 竞品搜索词配置表 ──
    op.create_table(
        "competitor_search_terms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market_code", sa.String(20), nullable=False, index=True,
                  comment="目标市场代码: VN, US, SA..."),
        sa.Column("brand", sa.String(80), nullable=False,
                  comment="品牌: AUX / TCL"),
        sa.Column("search_query", sa.String(500), nullable=False,
                  comment="搜索查询词"),
        sa.Column("language", sa.String(20), nullable=True,
                  comment="搜索语言"),
        sa.Column("product_type_hint", sa.String(60), nullable=True,
                  comment="产品类型提示"),
        sa.Column("priority", sa.Integer(), nullable=False, default=0,
                  comment="优先级"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True,
                  comment="是否启用"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True,
                  comment="上次使用时间"),
        sa.Column("use_count", sa.Integer(), nullable=False, default=0,
                  comment="被使用次数"),
        sa.Column("notes", sa.Text(), nullable=True,
                  comment="备注"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now(),
                  comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="竞品搜索词配置",
    )

    # ── 3. competitor_models 追加字段 ──
    op.add_column(
        "competitor_models",
        sa.Column("source", sa.String(32), nullable=False,
                  server_default=sa.text("'manual'"),
                  comment="数据来源: manual=人工录入, auto=自动采集"),
    )
    op.add_column(
        "competitor_models",
        sa.Column("source_url", sa.String(1024), nullable=True,
                  comment="来源 URL"),
    )


def downgrade() -> None:
    # 移除新增字段
    op.drop_column("competitor_models", "source_url")
    op.drop_column("competitor_models", "source")

    # 删除复合索引
    op.drop_index("idx_crawl_market_brand", table_name="competitor_crawls")

    # 删除表
    op.drop_table("competitor_search_terms")
    op.drop_table("competitor_crawls")
