"""competitor_crawler — 竞品自动采集包

模块:
- base.py:          抽象基类 BaseCompetitorCrawler + CompetitorItem/CrawlStats
- search_engine.py: 搜索引擎抽象 + Google CSE / DuckDuckGo 实现
- unit_normalizer.py:  空调参数单位归一化引擎
- regex_extractor.py:  正则参数提取器（LLM 降级方案）
- llm_extractor.py:    LLM 参数智能解析引擎（首选方案）
- matcher.py:         去重匹配器 CompetitorMatcher
- saver.py:           入库保存器 CompetitorSaver
"""

from typing import Any

from .base import BaseCompetitorCrawler, CompetitorItem, CrawlStats
from .llm_extractor import LLMParamExtractor
from .matcher import CompetitorMatcher
from .regex_extractor import RegexParamExtractor
from .saver import CompetitorSaver
from .search_engine import BaseSearchEngine, DuckDuckGoSearch, GoogleCSESearch
from .unit_normalizer import UnitNormalizer

# ── 搜索引擎注册表 ──
SEARCH_ENGINES: dict[str, type[BaseSearchEngine]] = {
    "google_cse": GoogleCSESearch,
    "ddg": DuckDuckGoSearch,
}
"""可用搜索引擎映射: google_cse → GoogleCSESearch, ddg → DuckDuckGoSearch"""

# ── 竞品爬虫注册表（由子类注册） ──
CRAWLER_REGISTRY: dict[str, type[BaseCompetitorCrawler]] = {}
"""市场代码 → 爬虫类 映射，子类通过 register_crawler() 注册"""


def register_crawler(market_code: str) -> Any:
    """装饰器：将爬虫类注册到 CRAWLER_REGISTRY

    Usage:
        @register_crawler("VN")
        class VietnamCrawler(BaseCompetitorCrawler): ...
    """
    def decorator(cls: type[BaseCompetitorCrawler]) -> type[BaseCompetitorCrawler]:
        CRAWLER_REGISTRY[market_code] = cls
        return cls
    return decorator


def create_crawler(
    market_code: str,
    brand: str,
    search_engine: BaseSearchEngine | None = None,
    config: dict[str, Any] | None = None,
) -> BaseCompetitorCrawler | None:
    """工厂函数：根据 market_code 查找注册的爬虫类并实例化

    如果未注册特定市场的爬虫，返回 None。
    可通过 `config` 传入 api_key、cse_id 等配置。
    """
    cls = CRAWLER_REGISTRY.get(market_code)
    if cls is None:
        return None
    return cls(market_code=market_code, brand=brand,
               search_engine=search_engine, config=config or {})


__all__ = [
    "BaseCompetitorCrawler",
    "BaseSearchEngine",
    "CompetitorItem",
    "CrawlStats",
    "CRAWLER_REGISTRY",
    "CompetitorMatcher",
    "CompetitorSaver",
    "DuckDuckGoSearch",
    "GoogleCSESearch",
    "LLMParamExtractor",
    "RegexParamExtractor",
    "SEARCH_ENGINES",
    "UnitNormalizer",
    "create_crawler",
    "register_crawler",
]
