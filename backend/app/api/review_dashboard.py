"""Review Dashboard API — 复盘汇总看板 (D4-3)

端点：
- GET /api/bi/review-summary — 复盘汇总数据
  评分分布、月度趋势、常见问题关键词、完成率
"""
import re
import logging
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_menu
from app.models.product_plan import ProductPlan, ProductPlanReview, ProductPlanStage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bi", tags=["BI分析看板"])

# 中英文停用词（排除无意义高频词）
_STOP_WORDS: frozenset[str] = frozenset({
    "的", "了", "和", "与", "及", "或", "是", "在", "有", "不",
    "很", "太", "到", "都", "要", "会", "能", "可以", "应该",
    "这个", "那个", "这些", "那些", "因为", "所以", "但是", "如果",
    "虽然", "而且", "然后", "没有", "不是", "被", "把", "从",
    "对", "为", "以", "等", "之", "中", "上", "下",
    "也", "还", "就", "而", "其", "它", "他", "她", "们",
    "the", "a", "an", "and", "or", "but", "in", "on", "at",
    "to", "for", "of", "with", "by", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might",
    "this", "that", "these", "those", "it", "its", "we", "they",
    "not", "no", "so", "if", "about", "into", "than", "can",
})


def _extract_keywords(lessons_list: list[str], top_n: int = 10) -> list[dict[str, object]]:
    """从经验教训文本中提取关键词频次

    使用正则提取中文词组和英文单词，过滤停用词和过短词，
    统计词频返回 TopN。
    """
    counter: Counter[str] = Counter()
    pattern = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z]\w*")

    for text_content in lessons_list:
        if not text_content or not text_content.strip():
            continue
        for match in pattern.finditer(text_content):
            word = match.group().strip().lower()
            if len(word) < 2:
                continue
            if word in _STOP_WORDS:
                continue
            if word.isdigit():
                continue
            counter[word] += 1

    return [
        {"word": word, "count": count}
        for word, count in counter.most_common(top_n)
    ]


@router.get("/review-summary")
def get_review_summary(
    start_month: Optional[str] = Query(None, description="起始月份 YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月份 YYYY-MM"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict[str, object]:
    """复盘汇总数据

    返回:
    - rating_distribution: 评分分布 {1: count, ..., 5: count}
    - monthly_trend: 月度趋势 [{month, avg_rating, count}, ...]
    - common_issues: 常见问题关键词频次 Top10
    - completion_rate: 完成率 {reviewed, total, rate}
    """
    result: dict[str, object] = {}

    # ── 基础筛选 ──
    review_base = db.query(ProductPlanReview)
    plan_base = db.query(ProductPlan)

    if start_month:
        review_base = review_base.filter(
            func.strftime("%Y-%m", ProductPlanReview.review_date) >= start_month
        )
    if end_month:
        review_base = review_base.filter(
            func.strftime("%Y-%m", ProductPlanReview.review_date) <= end_month
        )

    # ── 1. 评分分布 ──
    rating_rows = (
        review_base
        .with_entities(
            ProductPlanReview.rating,
            func.count(ProductPlanReview.id).label("cnt"),
        )
        .filter(ProductPlanReview.rating.isnot(None))
        .group_by(ProductPlanReview.rating)
        .order_by(ProductPlanReview.rating)
        .all()
    )
    rating_distribution: dict[str, int] = {str(i): 0 for i in range(1, 6)}
    for row in rating_rows:
        key = str(row.rating)
        if row.rating and 1 <= row.rating <= 5:
            rating_distribution[key] = row.cnt
    result["rating_distribution"] = rating_distribution

    # ── 2. 月度趋势 ──
    month_rows = (
        review_base
        .with_entities(
            func.strftime("%Y-%m", ProductPlanReview.review_date).label("month"),
            func.avg(ProductPlanReview.rating).label("avg_rating"),
            func.count(ProductPlanReview.id).label("count"),
        )
        .filter(ProductPlanReview.review_date.isnot(None))
        .group_by(text("month"))
        .order_by(text("month"))
        .all()
    )
    result["monthly_trend"] = [
        {
            "month": row.month,
            "avg_rating": round(float(row.avg_rating), 2) if row.avg_rating else 0.0,
            "count": row.count,
        }
        for row in month_rows
    ]

    # ── 3. 常见问题汇总 ──
    lessons_rows = review_base.with_entities(
        ProductPlanReview.lessons_learned
    ).filter(
        ProductPlanReview.lessons_learned.isnot(None),
        ProductPlanReview.lessons_learned != "",
    ).all()
    lessons_list: list[str] = [row.lessons_learned for row in lessons_rows]
    result["common_issues"] = _extract_keywords(lessons_list, top_n=10)

    # ── 4. 完成率 ──
    # 应复盘数 = 状态为已完结(APPROVED/RELEASED)的策划数
    terminal_statuses = [
        ProductPlanStage.APPROVED,
        ProductPlanStage.RELEASED,
    ]

    # 如果有时间筛选，也应用到策划过滤
    filtered_plan_base = plan_base
    if start_month:
        filtered_plan_base = filtered_plan_base.filter(
            func.strftime("%Y-%m", ProductPlan.created_at) >= start_month
        )
    if end_month:
        filtered_plan_base = filtered_plan_base.filter(
            func.strftime("%Y-%m", ProductPlan.created_at) <= end_month
        )

    total_plans = filtered_plan_base.count()
    terminal_plans = filtered_plan_base.filter(
        ProductPlan.status.in_(terminal_statuses)
    ).count()

    reviewed_count = review_base.count()

    result["completion_rate"] = {
        "total": terminal_plans,
        "reviewed": reviewed_count,
        "rate": round(reviewed_count / terminal_plans * 100, 2) if terminal_plans > 0 else 0.0,
    }

    return result
