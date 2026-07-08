"""PM角色相关查询逻辑 — 竞品动态摘要"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.competitor import CompetitorModel


def get_pm_competitor_summary(db: Session) -> Optional[dict]:
    """获取PM角色竞品动态摘要: 按市场统计竞品数量

    Args:
        db: 数据库会话

    Returns:
        dict: 包含 total（竞品总数）和 by_market（按市场分布）
    """
    comp_rows = (
        db.query(CompetitorModel.market, func.count(CompetitorModel.id))
        .group_by(CompetitorModel.market)
        .all()
    )
    return {
        "total": sum(row[1] for row in comp_rows),
        "by_market": {row[0] or "unknown": row[1] for row in comp_rows},
    }
