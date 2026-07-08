#!/usr/bin/env python3
"""竞品采集定时任务 — 由 Hermes cron 每日执行

用法:
    python /app/scripts/run_scheduled_crawl.py

流程:
    1. 创建数据库会话
    2. 查询所有活跃的市场×品牌组合
    3. 对每个组合执行批量爬取
    4. 收集统计结果并输出 JSON
"""
import asyncio
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("run_scheduled_crawl")


async def main() -> dict:
    """执行一次完整的竞品采集任务"""
    from app.core.database import SessionLocal
    from app.models.competitor_search_term import CompetitorSearchTerm
    from app.services.competitor_crawl_runner import run_batch_crawl, send_crawl_notification

    db = SessionLocal()
    try:
        logger.info("竞品采集 — 开始执行")

        # 查询所有活跃搜索词，按 market_code + brand 分组
        terms = (
            db.query(CompetitorSearchTerm)
            .filter(CompetitorSearchTerm.is_active == True)
            .order_by(CompetitorSearchTerm.market_code, CompetitorSearchTerm.brand, CompetitorSearchTerm.priority)
            .all()
        )

        # 分组
        groups = defaultdict(list)
        for term in terms:
            key = (term.market_code, term.brand)
            groups[key].append(term)

        if not groups:
            logger.warning("竞品采集 — 无活跃搜索词，跳过")
            return {"status": "skipped", "reason": "no_active_search_terms"}

        overall_stats = {
            "total_groups": len(groups),
            "total_search_terms": len(terms),
            "groups": {},
            "summary": {
                "new_added": 0,
                "updated": 0,
                "skipped": 0,
                "draft_count": 0,
                "total_found": 0,
                "failed": 0,
                "success": 0,
            },
        }

        # 对每个市场×品牌组合执行批量爬取
        for (market_code, brand) in sorted(groups.keys()):
            logger.info("竞品采集 — 开始分组: market=%s brand=%s", market_code, brand)
            try:
                logs = await run_batch_crawl(market_code, brand, db)

                group_stats = {
                    "search_terms": len(groups[(market_code, brand)]),
                    "crawl_logs": [],
                }
                for log in logs:
                    entry = {
                        "id": log.id,
                        "status": log.status,
                        "total_found": log.total_found or 0,
                        "new_added": log.new_added or 0,
                        "updated": log.updated or 0,
                        "skipped": log.skipped or 0,
                        "draft_count": log.draft_count or 0,
                    }
                    if log.error_message:
                        entry["error"] = log.error_message

                    group_stats["crawl_logs"].append(entry)

                    # 汇总
                    if log.status == "success":
                        overall_stats["summary"]["success"] += 1
                    elif log.status == "failed":
                        overall_stats["summary"]["failed"] += 1
                    overall_stats["summary"]["new_added"] += log.new_added or 0
                    overall_stats["summary"]["updated"] += log.updated or 0
                    overall_stats["summary"]["skipped"] += log.skipped or 0
                    overall_stats["summary"]["draft_count"] += log.draft_count or 0
                    overall_stats["summary"]["total_found"] += log.total_found or 0

                    # 发送通知
                    try:
                        send_crawl_notification(log, db)
                        db.commit()
                    except Exception as e:
                        logger.warning("通知创建失败: %s", e)

                overall_stats["groups"][f"{market_code}/{brand}"] = group_stats

            except Exception as exc:
                logger.error("分组爬取失败 market=%s brand=%s: %s", market_code, brand, exc)
                overall_stats["groups"][f"{market_code}/{brand}"] = {
                    "search_terms": len(groups[(market_code, brand)]),
                    "error": str(exc),
                }
                overall_stats["summary"]["failed"] += 1

        logger.info(
            "竞品采集 — 完成: 发现=%d 新增=%d 更新=%d 跳过=%d 草稿=%d 成功=%d 失败=%d",
            overall_stats["summary"]["total_found"],
            overall_stats["summary"]["new_added"],
            overall_stats["summary"]["updated"],
            overall_stats["summary"]["skipped"],
            overall_stats["summary"]["draft_count"],
            overall_stats["summary"]["success"],
            overall_stats["summary"]["failed"],
        )

        overall_stats["status"] = "completed"
        overall_stats["finished_at"] = datetime.utcnow().isoformat()
        return overall_stats

    except Exception as exc:
        logger.error("竞品采集 — 异常: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}
    finally:
        db.close()


if __name__ == "__main__":
    results = asyncio.run(main())
    print(json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(0 if results.get("status") != "error" else 1)
