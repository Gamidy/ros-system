"""竞品搜索词种子数据 — 预置各市场×品牌的搜索词"""
import logging
import sys
from app.core.database import SessionLocal
from app.models.competitor_search_term import CompetitorSearchTerm

logger = logging.getLogger(__name__)

# 搜索词定义: (market_code, brand, search_query, language, product_type_hint, priority, notes)
SEED_TERMS = [
    # ── 欧盟 AUX ──
    ("EU", "AUX", "AUX CLIMADESIGN MONO split AC specifications 2025", "en", "split-ac", 10,
     "CLIMADESIGN MONO 系列参数"),
    ("EU", "AUX", "AUX ARGO DELUXE split AC technical data sheet", "en", "split-ac", 10,
     "ARGO DELUXE 系列技术参数"),
    ("EU", "AUX", "AUX condizionatore split scheda tecnica 2025", "it", "split-ac", 20,
     "意大利语搜索"),
    ("EU", "AUX", "AUX air conditioner specs cooling capacity EER", "en", "split-ac", 30,
     "通用英文搜索"),
    ("EU", "AUX", "AUX climatiseur split fiche technique", "fr", "split-ac", 40,
     "法语搜索（覆盖法国市场）"),

    # ── 欧盟 TCL ──
    ("EU", "TCL", "TCL split AC specifications 2025", "en", "split-ac", 10,
     "TCL 欧盟机型参数"),
    ("EU", "TCL", "TCL condizionatore split scheda tecnica", "it", "split-ac", 20,
     "TCL 意大利语搜索"),

    # ── 欧盟 Midea ──
    ("EU", "Midea", "Midea split AC technical data sheet 2025", "en", "split-ac", 10,
     "美的欧盟机型"),
    ("EU", "Midea", "Midea condizionatore split scheda tecnica", "it", "split-ac", 20,
     "美的意大利语搜索"),

    # ── 加纳 AUX ──
    ("GH", "AUX", "AUX air conditioner Ghana price specifications", "en", "split-ac", 10,
     "AUX 加纳市场参数"),
    ("GH", "AUX", "AUX split AC AEER cooling capacity Ghana", "en", "split-ac", 20,
     "加纳 AEER 参数搜索"),
    ("GH", "TCL", "TCL air conditioner Ghana price specs", "en", "split-ac", 10,
     "TCL 加纳市场"),
    ("GH", "Midea", "Midea air conditioner Ghana specifications", "en", "split-ac", 10,
     "美的加纳市场"),

    # ── 澳大利亚 AUX ──
    ("AU", "AUX", "AUX air conditioner Australia specifications", "en", "split-ac", 10,
     "AUX 澳洲市场"),
    ("AU", "AUX", "AUX split AC AEER Australia cooling capacity", "en", "split-ac", 20,
     "澳洲 AEER 参数"),
    ("AU", "TCL", "TCL air conditioner Australia specs price", "en", "split-ac", 10,
     "TCL 澳洲市场"),
    ("AU", "Midea", "Midea air conditioner Australia specifications", "en", "split-ac", 10,
     "美的澳洲市场"),

    # ── 越南 AUX ──
    ("VN", "AUX", "AUX điều hòa không khí thông số kỹ thuật", "vi", "split-ac", 10,
     "AUX 越南语搜索"),
    ("VN", "AUX", "AUX máy lạnh split CSPF Việt Nam", "vi", "split-ac", 20,
     "越南 CSPF 参数搜索"),
    ("VN", "TCL", "TCL điều hòa không khí thông số", "vi", "split-ac", 10,
     "TCL 越南语搜索"),
    ("VN", "Midea", "Midea máy lạnh split CSPF thông số", "vi", "split-ac", 10,
     "美的越南语搜索"),

    # ── 美国 AUX ──
    ("US", "AUX", "AUX air conditioner USA SEER2 specifications", "en", "split-ac", 10,
     "AUX 美国 SEER2"),
    ("US", "AUX", "AUX mini split AC specifications cooling capacity", "en", "mini-split", 20,
     "AUX 美国迷你分体"),
    ("US", "Midea", "Midea air conditioner USA SEER2 specifications", "en", "split-ac", 10,
     "美的美国市场"),

    # ── 沙特 AUX ──
    ("SA", "AUX", "AUX مكيف هواء سبليت مواصفات", "ar", "split-ac", 10,
     "AUX 阿拉伯语搜索"),
    ("SA", "AUX", "AUX split AC Saudi Arabia SEER specifications", "en", "split-ac", 20,
     "沙特 SEER 参数"),
]


def seed_search_terms(dry_run: bool = False) -> int:
    """将 SEED_TERMS 写入数据库，已存在的跳过"""
    db = SessionLocal()
    added = 0
    try:
        for market_code, brand, query, lang, hint, priority, notes in SEED_TERMS:
            existing = db.query(CompetitorSearchTerm).filter(
                CompetitorSearchTerm.market_code == market_code,
                CompetitorSearchTerm.brand == brand,
                CompetitorSearchTerm.search_query == query,
            ).first()
            if existing:
                continue
            term = CompetitorSearchTerm(
                market_code=market_code,
                brand=brand,
                search_query=query,
                language=lang,
                product_type_hint=hint,
                priority=priority,
                is_active=True,
                notes=notes,
            )
            if not dry_run:
                db.add(term)
            added += 1
            print(f"  [+] [{market_code}] {brand}: {query[:50]}...")
        if not dry_run:
            db.commit()
            print(f"\n✅ 已写入 {added} 条搜索词")
        else:
            print(f"\n📋 模拟模式: 将写入 {added} 条搜索词 (dry_run=True)")
    except Exception as e:
        db.rollback()
        print(f"❌ 失败: {e}")
        raise
    finally:
        db.close()
    return added


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    seed_search_terms(dry_run=dry)
