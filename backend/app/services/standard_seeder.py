"""标准监控模块 — 预置数据初始化

在应用启动时确保 standard_regions 和 standard_categories 表有默认记录。
"""
import logging
from sqlalchemy.orm import Session

from app.models.standard import (
    StandardRegion, StandardCategory,
    REGION_PRESETS, CATEGORY_PRESETS,
)

logger = logging.getLogger(__name__)


def seed_standard_data(db: Session) -> None:
    """写入预置地区/分类（幂等：已存在则跳过）"""
    # ── 地区 ──
    existing_regions = {r.code for r in db.query(StandardRegion).all()}
    for preset in REGION_PRESETS:
        if preset["code"] not in existing_regions:
            region = StandardRegion(
                code=preset["code"],
                name=preset["name"],
                name_en=preset.get("name_en"),
                base_url=preset.get("base_url"),
                scan_method=preset["scan_method"],
                is_active=True,
                sort_order=len(existing_regions),
            )
            db.add(region)
            logger.info("Seed StandardRegion: %s", preset["code"])

    # ── 分类 ──
    existing_cats = {c.code for c in db.query(StandardCategory).all()}
    for idx, preset in enumerate(CATEGORY_PRESETS):
        if preset["code"] not in existing_cats:
            cat = StandardCategory(
                code=preset["code"],
                name=preset["name"],
                name_en=preset.get("name_en"),
                sort_order=idx,
            )
            db.add(cat)
            logger.info("Seed StandardCategory: %s", preset["code"])

    db.commit()
