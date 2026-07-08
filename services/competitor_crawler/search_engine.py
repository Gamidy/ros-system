"""搜索引擎抽象基类 + Google Custom Search / DuckDuckGo 实现

GoogleCSESearch 使用 Google Custom Search JSON API（需 API Key + CSE ID）。
DuckDuckGoSearch 直接请求 HTML 版搜索结果（免费，无需 API Key）。

两者均:
  - 使用 httpx 异步 HTTP 客户端
  - 随机 UA 轮换（10个真实浏览器 UA）
  - 请求间随机延迟 1~3s
"""

import abc
import asyncio
import logging
import random
import re
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

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


async def _random_delay() -> None:
    """随机延迟 1~3 秒"""
    await asyncio.sleep(random.uniform(1.0, 3.0))


def _random_ua() -> str:
    """返回随机 UA 字符串"""
    return random.choice(USER_AGENTS)


def _build_headers() -> dict[str, str]:
    """构造请求头（含随机 UA）"""
    return {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8,zh-CN;q=0.7,zh;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


# ── 抽象基类 ──


class BaseSearchEngine(abc.ABC):
    """搜索引擎抽象基类

    所有搜索引擎实现必须实现 search() 方法。
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    async def search(
        self,
        brand: str,
        market_code: str,
        query: str,
    ) -> list[dict]:
        """执行搜索

        Args:
            brand: 品牌名（AUX / TCL / Midea）
            market_code: 目标市场代码（VN / US / SA）
            query: 完整搜索查询词

        Returns:
            list[dict]: 搜索结果列表，每项包含:
                - title:   搜索结果标题
                - url:     目标页面链接
                - snippet: 摘要文本
                - source:  搜索引擎标识（"google" / "duckduckgo"）
        """
        ...


# ── Google Custom Search 实现 ──


class GoogleCSESearch(BaseSearchEngine):
    """Google Custom Search JSON API 封装

    需要:
        - Google Custom Search API Key（从 config["google_api_key"] 读取）
        - Custom Search Engine ID（从 config["google_cse_id"] 读取）

    文档: https://developers.google.com/custom-search/v1/overview
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, config: Optional[dict] = None) -> None:
        super().__init__(config)
        self.api_key: str = self.config.get("google_api_key", "")
        self.cse_id: str = self.config.get("google_cse_id", "")

        if not self.api_key or not self.cse_id:
            self.logger.warning(
                "Google CSE 未配置（缺 api_key 或 cse_id），"
                "搜索将返回空列表"
            )

    async def search(
        self,
        brand: str,
        market_code: str,
        query: str,
    ) -> list[dict]:
        """调用 Google Custom Search JSON API"""
        if not self.api_key or not self.cse_id:
            self.logger.warning("Google CSE 未完整配置，跳过搜索")
            return []

        params = {
            "key": self.api_key,
            "cx": self.cse_id,
            "q": query,
            "num": 10,           # 每页最多 10 条
            "hl": "en",
        }

        results: list[dict] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    self.BASE_URL,
                    params=params,
                    headers=_build_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google",
                })

            self.logger.info("Google CSE 返回 %d 条结果: query=%s", len(results), query)

        except httpx.HTTPStatusError as exc:
            self.logger.error("Google CSE HTTP 错误: %s", exc)
        except httpx.RequestError as exc:
            self.logger.error("Google CSE 请求失败: %s", exc)
        except ValueError as exc:
            self.logger.error("Google CSE 响应解析失败: %s", exc)

        return results


# ── DuckDuckGo HTML 搜索实现 ──


class DuckDuckGoSearch(BaseSearchEngine):
    """DuckDuckGo HTML 版搜索（免费，无需 API Key）

    直接请求 https://html.duckduckgo.com/html/ 并解析返回的 HTML。
    不需要 JavaScript 渲染，适用于简单的标题+URL+摘要提取。
    """

    BASE_URL = "https://html.duckduckgo.com/html"

    async def search(
        self,
        brand: str,
        market_code: str,
        query: str,
    ) -> list[dict]:
        """请求 DuckDuckGo HTML 搜索并解析结果"""
        results: list[dict] = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.post(
                    self.BASE_URL,
                    data={"q": query},
                    headers=_build_headers(),
                )
                resp.raise_for_status()

            results = self._parse_ddg_html(resp.text)
            self.logger.info("DuckDuckGo 返回 %d 条结果: query=%s", len(results), query)

        except httpx.HTTPStatusError as exc:
            self.logger.error("DuckDuckGo HTTP 错误: %s", exc)
        except httpx.RequestError as exc:
            self.logger.error("DuckDuckGo 请求失败: %s", exc)

        # 礼貌延迟
        await _random_delay()

        return results

    def _parse_ddg_html(self, html: str) -> list[dict]:
        """解析 DuckDuckGo HTML 搜索结果页面

        提取每一条结果的 标题、URL、摘要文本。
        使用 BeautifulSoup 进行轻量级 DOM 解析。
        """
        results: list[dict] = []
        soup = BeautifulSoup(html, "lxml")

        # DuckDuckGo HTML 版结果容器: class="result results_links"
        # 每条结果: <div class="result results_links_deep highlight_d">
        for result_div in soup.select(".result"):
            title_tag = result_div.select_one("h2.result__title a")
            if not title_tag:
                # 有时 title 不在 h2 内，尝试直接选 a.result__a
                title_tag = result_div.select_one("a.result__a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href: str = str(title_tag.get("href", "") or "")

            # DuckDuckGo 使用 rel 跳转链接，需提取真实 URL
            url = self._extract_real_url(href)

            # 摘要
            snippet_tag = result_div.select_one("a.result__snippet")
            if snippet_tag:
                snippet = snippet_tag.get_text(strip=True)
            else:
                snippet_tag = result_div.select_one(".result__snippet")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "duckduckgo",
            })

        return results

    @staticmethod
    def _extract_real_url(ddg_url: str) -> str:
        """从 DuckDuckGo 跳转链接中提取真实 URL

        DuckDuckGo 的链接格式:
          //duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com&rut=...
        或直接的外链。

        Args:
            ddg_url: DuckDuckGo 搜索结果中的 href 属性值

        Returns:
            str: 解码后的真实目标 URL
        """
        # 标准 DDG 跳转链接
        if "uddg=" in ddg_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(ddg_url)
            params = urllib.parse.parse_qs(parsed.query)
            encoded = params.get("uddg", [None])[0]
            if encoded:
                return urllib.parse.unquote(encoded)

        # 某些情况下是直接外链
        if ddg_url.startswith("//"):
            ddg_url = "https:" + ddg_url

        return ddg_url
