"""竞品爬取任务日志模型

记录每次自动竞品采集的执行情况，包括发现数/新增数/更新数/错误信息等。
复用 StandardCrawl 的设计模式。

表: competitor_crawls
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class CompetitorCrawl(Base):
    """竞品爬取任务日志"""
    __tablename__ = "competitor_crawls"

    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True,  # int)
    market_code: str = Column(
        String(20), nullable=False, index=True, comment="目标市场代码: VN, US, SA..."
    )
    brand: str = Column(
        String(80), nullable=False, index=True, comment="品牌: AUX / TCL"
    )
    started_at: datetime = Column(DateTime, nullable=False, comment="开始时间")
    finished_at: Optional[datetime] = Column(DateTime, comment="结束时间")
    status: str = Column(
        String(20), nullable=False, default="running",
        comment="状态: running|success|partial|failed"
    )

    # 搜索结果统计
    query_count: int = Column(
        Integer, nullable=False, default=0, comment="发起的搜索请求数"
    )
    pages_fetched: int = Column(
        Integer, nullable=False, default=0, comment="成功抓取的页面数"
    )

    # 参数解析统计
    total_found: int = Column(
        Integer, nullable=False, default=0, comment="本次发现的总条目数"
    )
    new_added: int = Column(
        Integer, nullable=False, default=0, comment="新增入库数"
    )
    updated: int = Column(
        Integer, nullable=False, default=0, comment="更新数"
    )
    skipped: int = Column(
        Integer, nullable=False, default=0, comment="跳过（重复/不相关/置信度过低）数"
    )
    draft_count: int = Column(
        Integer, nullable=False, default=0, comment="标记为 draft 待审数（confidence<0.4）"
    )

    # 错误信息
    error_message: Optional[str] = Column(Text, comment="失败时的错误详情")

    created_at: datetime = Column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )

    def __repr__(self) -> str:
        return (
            f"<CompetitorCrawl(id={self.id}, market={self.market_code!r}, "
            f"brand={self.brand!r}, status={self.status!r})>"
        )
