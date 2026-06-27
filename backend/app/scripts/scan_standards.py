#!/usr/bin/env python3
"""标准监控定时任务 — 由 Hermes cron 每日执行

用法:
    python -m app.scripts.scan_standards

流程:
    1. 创建数据库会话
    2. 执行所有活跃地区的爬取
    3. 对每个有新增的地区触发通知
    4. 输出 JSON 格式的运行结果
"""
import asyncio
import json
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("scan_standards")


async def main() -> dict:
    """执行一次完整的标准爬取任务"""
    from app.core.database import SessionLocal
    from app.models.standard import StandardRegion
    from app.services.standard_crawler import run_all_active_crawlers
    from app.services.standard_notifier import notify_standard_update

    db = SessionLocal()
    try:
        logger.info("标准监控 — 开始爬取")
        results = await run_all_active_crawlers(db)

        # 对每个有新增的地区触发通知
        region_map = {r.id: r for r in db.query(StandardRegion).all()}
        for code, stats in results.items():
            if stats.get("error") or stats.get("new_added", 0) == 0:
                continue
            region = next((r for r in region_map.values() if r.code == code), None)
            if region:
                notify_standard_update(db, region.id, region.name, stats)

        logger.info("标准监控 — 爬取完成: %s", json.dumps(results, ensure_ascii=False))
        return results

    except Exception as exc:
        logger.error("标准监控 — 爬取异常: %s", exc, exc_info=True)
        return {"error": str(exc)}
    finally:
        db.close()


if __name__ == "__main__":
    results = asyncio.run(main())
    print(json.dumps(results, indent=2, ensure_ascii=False))
    sys.exit(0 if "error" not in results else 1)
