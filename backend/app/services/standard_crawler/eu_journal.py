"""EU Official Journal — RSS Feed 爬虫

从 EU Publications Office 的 RSS feed 获取最新标准/法规更新。
筛选空调/热泵/制冷相关条目。
"""
import logging
from typing import Optional

import httpx
import feedparser

from app.services.standard_crawler.base import BaseStandardCrawler, StandardItem
from app.services.standard_crawler.parser import StandardParser

logger = logging.getLogger(__name__)

# EU Official Journal RSS — 能源/环境/产品法规
EU_RSS_URLS: list[str] = [
    "https://eur-lex.europa.eu/oj/rss/oj-en.xml",                          # 全部OJ
    "https://eur-lex.europa.eu/oj/rss/sector-15-en.xml",                   # 环境
    "https://eur-lex.europa.eu/oj/rss/sector-17-en.xml",                   # 能源
]

parser = StandardParser()


class EUJournalCrawler(BaseStandardCrawler):
    """EU Official Journal RSS 爬虫"""

    def __init__(self, region_code: str, region_id: int, config: Optional[dict] = None):
        super().__init__(region_code, region_id, config)
        self.rss_urls = EU_RSS_URLS

    async def fetch(self) -> list[dict]:
        """抓取所有 RSS feed → 合并为原始条目列表"""
        all_entries: list[dict] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for url in self.rss_urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries:
                        all_entries.append({
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "summary": entry.get("summary", ""),
                        })
                    self.logger.info("RSS %s: %d 条", url, len(feed.entries))
                except Exception as exc:
                    self.logger.warning("RSS 抓取失败 %s: %s", url, exc)
        return all_entries

    async def parse(self, raw_items: list[dict]) -> list[StandardItem]:
        """遍历条目 → 过滤空调相关 → 提取标准编号"""
        items: list[StandardItem] = []
        seen_numbers: set[str] = set()

        for entry in raw_items:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            combined = f"{title} {summary}"

            # 仅保留空调/热泵/制冷相关
            if not parser.is_hvac_related(combined):
                continue

            # 提取标准编号
            std_number = parser.extract_std_number(combined)
            if not std_number:
                # 没有标准编号的法规（如行政通知）— 用标题前60字符当ID
                std_number = title[:60]
                if not std_number:
                    continue

            # 去重（同编号只保留一次）
            if std_number in seen_numbers:
                continue
            seen_numbers.add(std_number)

            # 推断分类和影响
            categories = parser.classify_category(combined)
            impact = parser.assess_impact(title, summary)
            eff_date = parser.extract_effective_date(combined)

            items.append(StandardItem(
                std_number=std_number,
                title=title,
                region_code="EU",
                source_url=entry.get("link", ""),
                effective_date=eff_date,
                status="active" if "repeal" not in title.lower() else "superseded",
                raw_text=summary[:2000],
                category_hints=categories,
                impact_level=impact,
            ))

        return items
