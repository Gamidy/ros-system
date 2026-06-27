"""定时竞品采集脚本 — 由 Cron 调度执行

按优先级依次采集所有活跃搜索词对应的市场×品牌数据。
每天凌晨2点执行一次。

Usage:
    python scripts/run_scheduled_crawl.py
"""
import asyncio
import logging
from datetime import datetime

from app.core.database import SessionLocal
from app.models.competitor_search_term import CompetitorSearchTerm
from app.services.competitor_crawl_runner import run_batch_crawl, send_crawl_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduled_crawl")


async def run_scheduled_crawl():
    """找出所有活跃搜索词中的唯一 (market_code, brand) 组合，逐个批量执行"""
    db = SessionLocal()
    try:
        # 获取所有唯一 (market_code, brand) 组合
        from sqlalchemy import true
        rows = (
            db.query(
                CompetitorSearchTerm.market_code,
                CompetitorSearchTerm.brand,
            )
            .filter(CompetitorSearchTerm.is_active.is_(True))
            .distinct()
            .all()
        )
        if not rows:
            logger.info("没有活跃搜索词，跳过本次定时采集")
            return

        total_terms = db.query(CompetitorSearchTerm).filter(
            CompetitorSearchTerm.is_active.is_(True)
        ).count()
        logger.info("定时采集启动: %d 个市场x品牌组合, %d 个搜索词",
                     len(rows), total_terms)

        results = []
        for market_code, brand in rows:
            logger.info("开始采集: market=%s brand=%s", market_code, brand)
            try:
                logs = await run_batch_crawl(market_code, brand, db)
                for log in logs:
                    send_crawl_notification(log, db)
                    results.append(log)
                db.commit()
                logger.info("采集完成: market=%s brand=%s -> %d 条日志",
                            market_code, brand, len(logs))
            except Exception as e:
                db.rollback()
                logger.error("采集失败: market=%s brand=%s -> %s",
                             market_code, brand, e)

        logger.info("定时采集结束: %d 个组合, %d 条日志",
                    len(rows), len(results))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_scheduled_crawl())
