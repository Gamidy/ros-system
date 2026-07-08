"""竞品爬取编排层 — 执行、批量执行、通知

提供三个核心功能:
  1. run_crawl()        — 对单个搜索词执行完整爬取管道
  2. run_batch_crawl()  — 对指定市场×品牌的所有活跃搜索词批量执行
  3. send_crawl_notification() — 爬取完成后创建系统通知
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.competitor_crawl import CompetitorCrawl
from app.models.competitor_search_term import CompetitorSearchTerm
from app.models.alert import Notification
from app.services.competitor_crawler import (
    CompetitorItem,
    CompetitorMatcher,
    CompetitorSaver,
    CrawlStats,
    SEARCH_ENGINES,
    create_crawler,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 核心执行
# ═══════════════════════════════════════════════════════════════════════


async def run_crawl(search_term_id: int, db: Session) -> CompetitorCrawl:
    """对指定搜索词执行完整的爬取管道

    Pipeline:  搜索 → 抓取 → 解析 → 去重保存

    1. 从 ``competitor_search_terms`` 加载搜索词并校验
    2. 创建 ``competitor_crawls`` 日志记录 (status=running)
    3. 通过 ``SEARCH_ENGINES`` 注册表实例化搜索引擎
    4. 通过 ``create_crawler()`` 工厂获取市场对应的爬虫实例
    5. 执行搜索 → fetch → parse 流程
    6. 使用 ``CompetitorSaver`` + ``CompetitorMatcher`` 逐条去重保存
    7. 更新日志状态和统计，并更新搜索词使用记录

    Args:
        search_term_id: ``CompetitorSearchTerm`` 的主键 ID
        db: 数据库 Session（调用方负责事务边界）

    Returns:
        已持久化的 ``CompetitorCrawl`` 日志记录

    Raises:
        ValueError: 搜索词不存在或未启用
        RuntimeError: 无可用搜索引擎或未注册市场爬虫
    """
    # ── 1. 加载搜索词 ──
    term: Optional[CompetitorSearchTerm] = (
        db.query(CompetitorSearchTerm)
        .filter(CompetitorSearchTerm.id == search_term_id)
        .first()
    )
    if term is None:
        raise ValueError(f"搜索词不存在: id={search_term_id}")
    if not term.is_active:
        raise ValueError(
            f"搜索词未启用: id={search_term_id}, query={term.search_query!r}"
        )

    market_code = term.market_code
    brand = term.brand
    query = term.search_query

    # ── 2. 创建爬取日志 ──
    crawl_log = CompetitorCrawl(
        market_code=market_code,
        brand=brand,
        started_at=datetime.utcnow(),
        status="running",
    )
    db.add(crawl_log)
    db.flush()
    log_id = crawl_log.id
    logger.info(
        "爬取开始: id=%d market=%s brand=%s query=%s",
        log_id, market_code, brand, query,
    )

    stats = CrawlStats()

    try:
        # ── 3. 创建搜索引擎 ──
        engine_cls = SEARCH_ENGINES.get("ddg") or next(iter(SEARCH_ENGINES.values()), None)
        if engine_cls is None:
            raise RuntimeError("无可用搜索引擎，请先配置搜索引擎")
        search_engine = engine_cls()

        # ── 4. 创建爬虫实例 ──
        crawler = create_crawler(
            market_code=market_code,
            brand=brand,
            search_engine=search_engine,
        )
        if crawler is None:
            raise RuntimeError(
                f"未注册市场 {market_code!r} 的爬虫，无法执行爬取"
            )

        # ── 5. 搜索 ──
        search_results = await search_engine.search(
            brand=brand,
            market_code=market_code,
            query=query,
        )
        crawl_log.query_count = len(search_results)
        logger.info("搜索结果: %d 条 (query=%s)", len(search_results), query)

        # ── 6. 抓取页面 ──
        raw_items = await crawler.fetch(search_results)
        crawl_log.pages_fetched = len(raw_items)
        logger.info("页面抓取: %d 页", len(raw_items))

        # ── 7. 解析条目 ──
        parsed: list[CompetitorItem] = await crawler.parse(raw_items)
        stats.total_found = len(parsed)
        logger.info("条目解析: %d 条", len(parsed))

        # ── 8. 去重保存 ──
        saver = CompetitorSaver(db)
        for item in parsed:
            existing = CompetitorMatcher.find_existing(
                db, item.brand, item.model, item.market,
            )
            if existing is None:
                # 全新记录
                saver.save_new(item)
                stats.new_added += 1
            elif item.confidence < 0.4:
                # 置信度过低 → draft
                stats.draft_count += 1
            elif CompetitorMatcher.should_update(item, existing):
                diff = CompetitorMatcher.compute_diff(item, existing)
                if diff:
                    saver.update_existing(item, existing)
                    stats.updated += 1
                else:
                    stats.skipped += 1
            else:
                stats.skipped += 1

        # ── 9. 更新爬取日志 ──
        crawl_log.finished_at = datetime.utcnow()
        crawl_log.status = "success" if not stats.error else "partial"
        crawl_log.total_found = stats.total_found
        crawl_log.new_added = stats.new_added
        crawl_log.updated = stats.updated
        crawl_log.skipped = stats.skipped
        crawl_log.draft_count = stats.draft_count

        # ── 10. 更新搜索词使用记录 ──
        term.last_used_at = datetime.utcnow()
        term.use_count = (term.use_count or 0) + 1

        db.commit()
        logger.info(
            "爬取完成: 发现=%d 新增=%d 更新=%d 跳过=%d 草稿=%d",
            stats.total_found, stats.new_added, stats.updated,
            stats.skipped, stats.draft_count,
        )

    except Exception as exc:
        logger.exception(f"unexpected: {exc}")
        db.rollback()
        stats.error = str(exc)
        logger.error("爬取失败: %s", exc, exc_info=True)

        # 重新获取日志对象并标记失败
        crawl_log = (
            db.query(CompetitorCrawl)
            .filter(CompetitorCrawl.id == log_id)
            .first()
        )
        if crawl_log:
            crawl_log.status = "failed"
            crawl_log.error_message = str(exc)[:2000]
            crawl_log.finished_at = datetime.utcnow()
            crawl_log.total_found = stats.total_found
            db.commit()

        raise

    return crawl_log


# ═══════════════════════════════════════════════════════════════════════
# 批量执行
# ═══════════════════════════════════════════════════════════════════════


async def run_batch_crawl(
    market_code: str,
    brand: str,
    db: Session,
) -> list[CompetitorCrawl]:
    """对指定市场+品牌的所有活跃搜索词执行批量爬取

    按 priority 升序逐个执行，单个搜索词失败不中断整体流程。

    Args:
        market_code: 目标市场代码 (VN / US / SA …)
        brand:       品牌 (AUX / TCL / Midea …)
        db:          数据库 Session

    Returns:
        本次成功完成的爬取日志列表（每个搜索词对应一条）
    """
    terms: list[CompetitorSearchTerm] = (
        db.query(CompetitorSearchTerm)
        .filter(
            CompetitorSearchTerm.market_code == market_code,
            CompetitorSearchTerm.brand == brand,
            CompetitorSearchTerm.is_active == True,
        )
        .order_by(CompetitorSearchTerm.priority.asc())
        .all()
    )

    if not terms:
        logger.warning(
            "未找到活跃搜索词: market=%s brand=%s", market_code, brand,
        )
        return []

    logs: list[CompetitorCrawl] = []
    for term in terms:
        try:
            log = await run_crawl(term.id, db)
            logs.append(log)
        except Exception as exc:
            logger.error("搜索词 %d 爬取失败: %s", term.id, exc)
            # 继续执行下一个搜索词
            continue

    return logs


# ═══════════════════════════════════════════════════════════════════════
# 通知
# ═══════════════════════════════════════════════════════════════════════


def send_crawl_notification(crawl_log: CompetitorCrawl, db: Session) -> Notification:
    """爬取完成后在 ``notifications`` 表创建一条系统通知

    Args:
        crawl_log: 已完成的爬取日志记录
        db:        数据库 Session

    Returns:
        已持久化的 ``Notification`` 实例
    """
    status_emoji = {
        "success": "✅",
        "partial": "⚠️",
        "failed": "❌",
        "running": "🔄",
    }
    emoji = status_emoji.get(crawl_log.status, "ℹ️")

    title = f"{emoji} 竞品爬取 {crawl_log.status}"
    content = (
        f"市场: {crawl_log.market_code} | "
        f"品牌: {crawl_log.brand} | "
        f"状态: {crawl_log.status}"
    )

    if crawl_log.status == "failed":
        content += f" | 错误: {crawl_log.error_message or '未知'}"
    else:
        content += (
            f" | 发现: {crawl_log.total_found}"
            f" | 新增: {crawl_log.new_added}"
            f" | 更新: {crawl_log.updated}"
            f" | 跳过: {crawl_log.skipped}"
            f" | 草稿: {crawl_log.draft_count}"
        )

    notification = Notification(
        target_user="system",
        channel="system",
        title=title,
        content=content,
        is_sent=True,
        sent_at=datetime.utcnow(),
    )
    db.add(notification)
    db.flush()
    logger.info("爬取通知已创建: id=%d", notification.id)

    return notification
