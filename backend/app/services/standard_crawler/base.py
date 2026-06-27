"""标准爬虫 — 抽象基类与共享数据模型"""
import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class StandardItem:
    """爬虫爬取到的单条标准条目（未入库前的数据结构）"""
    std_number: str                                          # 标准编号
    title: str                                               # 标题（原文）
    region_code: str                                         # 地区代码: EU/US/SA/IEC
    source_url: str                                          # 原文链接
    effective_date: Optional[str] = None                     # 生效日期（原文格式，待解析）
    version: Optional[str] = None                            # 版本号
    amendment: Optional[str] = None                          # 修订信息
    status: str = "active"                                   # 状态
    raw_text: Optional[str] = None                           # 原始全文摘要
    category_hints: list[str] = field(default_factory=list)  # 分类线索
    impact_level: str = "medium"                             # 默认影响等级


@dataclass
class CrawlStats:
    """单次爬取统计"""
    total_fetched: int = 0
    new_added: int = 0
    updated: int = 0
    skipped: int = 0
    error_message: Optional[str] = None


class BaseStandardCrawler(abc.ABC):
    """标准爬虫抽象基类

    子类必须实现:
    - fetch()    → 从数据源获取原始数据
    - parse()    → 解析为标准条目列表

    run() 方法封装了完整的 fetch→parse→dedup→save 流程。
    """

    def __init__(self, region_code: str, region_id: int, config: Optional[dict] = None):
        self.region_code = region_code
        self.region_id = region_id
        self.config = config or {}
        self.logger = logging.getLogger(f"crawler.{region_code}")

    @abc.abstractmethod
    async def fetch(self) -> list[dict]:
        """从数据源获取原始数据

        Returns:
            list[dict]: 原始条目列表（结构由各子类定义）
        """
        ...

    @abc.abstractmethod
    async def parse(self, raw_items: list[dict]) -> list[StandardItem]:
        """将原始数据解析为标准化条目

        Args:
            raw_items: fetch() 返回的原始数据

        Returns:
            list[StandardItem]: 解析后的标准条目
        """
        ...

    async def run(self, db: Session) -> CrawlStats:
        """完整执行流程: fetch → parse → dedup → save → 统计"""
        stats = CrawlStats()

        try:
            raw_items = await self.fetch()
            stats.total_fetched = len(raw_items)

            parsed = await self.parse(raw_items)
            self.logger.info("解析完成: %d 条（原始 %d 条）", len(parsed), len(raw_items))

            for item in parsed:
                result = self._save_item(db, item)
                if result == "new":
                    stats.new_added += 1
                elif result == "updated":
                    stats.updated += 1
                else:
                    stats.skipped += 1

            db.commit()
            self.logger.info(
                "爬取完成: 新增=%d 更新=%d 跳过=%d",
                stats.new_added, stats.updated, stats.skipped,
            )

        except Exception as exc:
            db.rollback()
            stats.error_message = str(exc)
            self.logger.error("爬取失败: %s", exc, exc_info=True)

        return stats

    def _save_item(self, db: Session, item: StandardItem) -> str:
        """将一条标准条目写入数据库（幂等）"""
        from app.models.standard import Standard

        # 查找是否已存在（同地区 + 同编号）
        existing = (
            db.query(Standard)
            .filter(
                Standard.region_id == self.region_id,
                Standard.std_number == item.std_number,
            )
            .first()
        )

        # 日期解析
        eff_date = self._parse_date(item.effective_date) if item.effective_date else None

        if existing:
            # 更新已有记录
            changed = False
            if item.title and str(item.title) != str(existing.title or ""):
                existing.title = item.title
                changed = True
            if item.version and str(item.version) != str(existing.version or ""):
                existing.version = item.version
                changed = True
            if item.amendment and str(item.amendment) != str(existing.amendment or ""):
                existing.amendment = item.amendment
                changed = True
            if eff_date and eff_date != existing.effective_date:
                existing.effective_date = eff_date
                changed = True
            if item.raw_text:
                existing.source_text = item.raw_text[:5000]

            if changed:
                return "updated"
            return "skipped"
        else:
            # 新增记录
            std = Standard(
                region_id=self.region_id,
                std_number=item.std_number,
                title=item.title,
                source_url=item.source_url,
                effective_date=eff_date,
                version=item.version,
                amendment=item.amendment,
                status=item.status,
                source_text=item.raw_text[:5000] if item.raw_text else None,
                impact_level=item.impact_level,
                created_by="system",
            )
            db.add(std)
            return "new"

    @staticmethod
    def _parse_date(date_str: str) -> date | None:
        """解析多种日期格式 → date 对象"""
        from datetime import date
        import re

        # 尝试常见格式
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d %B %Y",
            "%B %d, %Y",
            "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except (ValueError, AttributeError):
                continue

        # 尝试提取年份
        m = re.search(r"(\d{4})", date_str)
        if m:
            return date(int(m.group(1)), 1, 1)

        return None
