"""竞品搜索词配置模型

存储每个市场×品牌的搜索查询词，支持多语言、自定义排序。
管理员可通过管理 API 动态增删改。

表: competitor_search_terms
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from app.core.database import Base


class CompetitorSearchTerm(Base):
    """竞品搜索词配置"""
    __tablename__ = "competitor_search_terms"

    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True,  # int)
    market_code: str = Column(
        String(20), nullable=False, index=True, comment="目标市场代码: VN, US, SA..."
    )
    brand: str = Column(
        String(80), nullable=False, index=True, comment="品牌: AUX / TCL"
    )
    search_query: str = Column(
        String(500), nullable=False, comment="搜索查询词（当地语言）"
    )
    language: Optional[str] = Column(
        String(20), comment="搜索语言: en, vi, ar, pt, ru..."
    )
    product_type_hint: Optional[str] = Column(
        String(60), comment="产品类型提示: split-ac, window-ac, portable..."
    )
    priority: int = Column(
        Integer, nullable=False, default=0, comment="优先级（数字越小越优先）"
    )
    is_active: bool = Column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )

    # 上次使用情况
    last_used_at: Optional[datetime] = Column(DateTime, comment="上次被爬取使用的时间")
    use_count: int = Column(
        Integer, nullable=False, default=0, comment="被使用次数"
    )

    notes: Optional[str] = Column(Text, comment="备注（搜索词来源、翻译说明等）")

    created_at: datetime = Column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: datetime = Column(
        DateTime, nullable=False, server_default=func.now(),
        onupdate=func.now(), comment="更新时间"
    )

    def __repr__(self) -> str:
        return (
            f"<CompetitorSearchTerm(id={self.id}, market={self.market_code!r}, "
            f"brand={self.brand!r}, query={self.search_query!r})>"
        )
