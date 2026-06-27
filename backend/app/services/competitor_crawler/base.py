"""竞品爬虫 — 抽象基类与共享数据模型

遵循现有 standard_crawler.base 的 fetch→parse→dedup→save 流程模式。
子类必须实现 fetch() 和 parse()，run() 封装了完整生命周期。

表结构参考: app.models.competitor_crawl.CompetitorCrawl
"""

import abc
import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── 10 个真实 User-Agent 轮换 ──
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
    "Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:127.0) "
    "Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 "
    "Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Vivaldi/6.7",
]


async def random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """随机延迟，避免触发目标反爬"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def get_random_ua() -> str:
    """从 UA 池中随机选取一个"""
    return random.choice(USER_AGENTS)


# ── 数据模型 ──


@dataclass
class CompetitorItem:
    """竞品条目（未入库前的数据结构）

    由 parse() 方法产出，经 _save_item() 去重后写入数据库。
    """
    brand: str                          # 品牌: AUX / TCL / Midea
    model: str                          # 具体型号: AS-24HF3A / MS-24UY
    market: str                         # 目标市场代码: VN / US / SA
    source_url: str                     # 来源页面 URL
    raw_params: dict = field(default_factory=dict)   # 原始参数键值对（后续阶段解析）
    confidence: float = 1.0             # 置信度 0.0~1.0（<0.4 → draft）
    raw_text: str = ""                  # 原始页面文本摘要


@dataclass
class CrawlStats:
    """单次爬取执行统计

    字段与 CompetitorCrawl 模型一一对应，便于写入日志表。
    """
    total_found: int = 0                # 本次发现的总条目数
    new_added: int = 0                  # 新增入库数
    updated: int = 0                    # 更新数
    skipped: int = 0                    # 跳过（重复/不相关/置信度过低）数
    error: Optional[str] = None         # 错误信息
    draft_count: int = 0                # 标记为 draft 待审数（confidence < 0.4）


# ── 抽象基类 ──


class BaseCompetitorCrawler(abc.ABC):
    """竞品爬虫抽象基类

    子类必须实现:
        fetch(search_results) → list[dict]   从搜索结果页面抓取原始数据
        parse(raw_items)      → list[CompetitorItem]  解析为结构化条目

    run() 封装了完整的 搜索→抓取→解析→去重→保存 流程，
    并自动创建/更新 competitor_crawls 日志记录。
    """

    def __init__(
        self,
        market_code: str,
        brand: str,
        search_engine,                  # BaseSearchEngine 实例
        config: Optional[dict] = None,
    ) -> None:
        self.market_code = market_code
        self.brand = brand
        self.search_engine = search_engine
        self.config = config or {}
        self.logger = logging.getLogger(f"competitor.{market_code}.{brand}")

    # ── 子类必须实现的抽象方法 ──

    @abc.abstractmethod
    async def fetch(self, search_results: list[dict]) -> list[dict]:
        """从搜索结果中抓取各产品页面原始数据

        Args:
            search_results: search_engine.search() 返回的搜索结果列表

        Returns:
            list[dict]: 各产品页面的原始数据（结构由子类定义）
        """
        ...

    @abc.abstractmethod
    async def parse(self, raw_items: list[dict]) -> list[CompetitorItem]:
        """将原始数据解析为结构化的 CompetitorItem 列表

        Args:
            raw_items: fetch() 返回的原始数据

        Returns:
            list[CompetitorItem]: 解析后的竞品条目
        """
        ...

    # ── 核心执行流程 ──

    async def run(self, db: Session) -> CrawlStats:
        """完整执行流程: 搜索 → 抓取 → 解析 → 去重 → 保存

        1. 创建 CompetitorCrawl 日志记录（status=running）
        2. 调用 search_engine.search() 获取搜索结果
        3. 调用 fetch() 抓取产品页原始数据
        4. 调用 parse() 解析为 CompetitorItem 列表
        5. 逐条去重保存到数据库
        6. 更新日志记录并提交事务
        """
        stats = CrawlStats()
        crawl_log = None

        try:
            # ── 1. 创建爬取日志 ──
            from app.models.competitor_crawl import CompetitorCrawl

            crawl_log = CompetitorCrawl(
                market_code=self.market_code,
                brand=self.brand,
                started_at=datetime.utcnow(),
                status="running",
            )
            db.add(crawl_log)
            db.flush()
            self.logger.info("爬取开始: market=%s brand=%s", self.market_code, self.brand)

            # ── 2. 搜索 ──
            query = self._build_query()
            search_results = await self.search_engine.search(
                brand=self.brand,
                market_code=self.market_code,
                query=query,
            )
            crawl_log.query_count = len(search_results)
            self.logger.info("搜索结果: %d 条 (query=%s)", len(search_results), query)

            # ── 3. 抓取 ──
            raw_items = await self.fetch(search_results)
            crawl_log.pages_fetched = len(raw_items)
            self.logger.info("页面抓取: %d 页", len(raw_items))

            # ── 4. 解析 ──
            parsed = await self.parse(raw_items)
            stats.total_found = len(parsed)
            self.logger.info("条目解析: %d 条（原始 %d 条）", len(parsed), len(raw_items))

            # ── 5. 去重保存 ──
            for item in parsed:
                result = self._save_item(db, item)
                if result == "new":
                    stats.new_added += 1
                elif result == "updated":
                    stats.updated += 1
                elif result == "draft":
                    stats.draft_count += 1
                else:  # "skipped"
                    stats.skipped += 1

            # ── 6. 更新日志 ──
            crawl_log.finished_at = datetime.utcnow()
            crawl_log.status = "success" if not stats.error else "partial"
            crawl_log.total_found = stats.total_found
            crawl_log.new_added = stats.new_added
            crawl_log.updated = stats.updated
            crawl_log.skipped = stats.skipped
            crawl_log.draft_count = stats.draft_count

            db.commit()
            self.logger.info(
                "爬取完成: 发现=%d 新增=%d 更新=%d 跳过=%d 草稿=%d",
                stats.total_found, stats.new_added, stats.updated,
                stats.skipped, stats.draft_count,
            )

        except Exception as exc:
            db.rollback()
            stats.error = str(exc)
            self.logger.error("爬取失败: %s", exc, exc_info=True)

            # 即使失败也要更新日志状态
            if crawl_log is not None and crawl_log.id:
                try:
                    crawl_log.status = "failed"
                    crawl_log.error_message = str(exc)[:2000]
                    crawl_log.finished_at = datetime.utcnow()
                    db.add(crawl_log)
                    db.commit()
                except Exception:
                    db.rollback()

        return stats

    # ── 内部方法 ──

    def _build_query(self) -> str:
        """构造搜索引擎查询词

        子类可覆写以定制查询策略。
        默认模式: "{brand} split AC specs {market}"
        """
        return f"{self.brand} split AC specs {self.market_code}"

    def _save_item(self, db: Session, item: CompetitorItem) -> str:
        """去重保存单条竞品条目到数据库

        暂存实现 — 当前只做日志记录和置信度过滤。
        等待 CompetitorProduct 模型就绪后完善真实入库逻辑。

        Returns:
            str: 操作结果类型 — "new" / "updated" / "draft" / "skipped"
        """
        # 置信度过滤: < 0.4 直接标记为 draft
        if item.confidence < 0.4:
            self.logger.debug("draft 待审: brand=%s model=%s confidence=%.2f",
                              item.brand, item.model, item.confidence)
            return "draft"

        # TODO: Stage 2 — 引入 CompetitorProduct 模型后的真实去重保存逻辑
        # 届时在这里实现:
        #   1. db.query(CompetitorProduct).filter_by(brand=item.brand, model=item.model).first()
        #   2. 存在则更新，不存在则新增
        #   3. 返回 "new" / "updated" / "skipped"
        self.logger.debug("待入库条目: brand=%s model=%s 来源=%s confidence=%.2f",
                          item.brand, item.model, item.source_url, item.confidence)
        return "skipped"
