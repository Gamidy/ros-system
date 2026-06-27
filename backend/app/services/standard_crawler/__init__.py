"""标准爬虫模块 — 包初始化 + 工厂函数"""
from typing import Optional

from sqlalchemy.orm import Session

from app.services.standard_crawler.base import BaseStandardCrawler
from app.services.standard_crawler.eu_journal import EUJournalCrawler

# 爬虫注册表 — code → class
CRAWLER_REGISTRY: dict[str, type[BaseStandardCrawler]] = {
    "EU": EUJournalCrawler,
    # Phase 3 后续实现:
    # "US": USFederalRegisterCrawler,
    # "SA": SASOScanner,
    # "IEC": IECSanner,
}


def create_crawler(region_code: str, region_id: int,
                   config: Optional[dict] = None) -> Optional[BaseStandardCrawler]:
    """工厂函数: 根据地区代码创建对应的爬虫实例"""
    crawler_cls = CRAWLER_REGISTRY.get(region_code)
    if not crawler_cls:
        return None
    return crawler_cls(region_code, region_id, config)


async def run_all_active_crawlers(db: Session) -> dict[str, dict]:
    """执行所有已启用地区的爬取任务

    Returns:
        dict: {region_code: {new_added, updated, skipped, error}}
    """
    from app.models.standard import StandardRegion

    regions = db.query(StandardRegion).filter(
        StandardRegion.is_active.is_(True)
    ).all()

    results: dict[str, dict] = {}
    for region in regions:
        crawler = create_crawler(region.code, region.id, region.scan_config)
        if not crawler:
            results[region.code] = {"error": f"未注册爬虫: {region.code}"}
            continue

        stats = await crawler.run(db)
        results[region.code] = {
            "new_added": stats.new_added,
            "updated": stats.updated,
            "skipped": stats.skipped,
            "error": stats.error_message,
        }

    return results
