"""竞品去重匹配器 — 查找、去重、差异计算、更新判定"""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.competitor import CompetitorModel
from .base import CompetitorItem


class CompetitorMatcher:
    """竞品去重匹配器

    负责查找已存在记录、判断是否为重复、计算差异、判断是否应更新。
    """

    # 核心字段 — 变化时应优先更新
    CORE_FIELDS: set[str] = {
        "cooling_capacity_w",
        "heating_capacity_w",
        "eer",
        "cspf",
        "energy_rating",
    }

    # ── 工具方法 ──

    @staticmethod
    def _normalize(text: str) -> str:
        """忽略大小写和空格的归一化"""
        return text.lower().replace(" ", "").replace("\u00a0", "")

    # ── 查找 ──

    @staticmethod
    def find_existing(
        db: Session,
        brand: str,
        model: str,
        market: str,
    ) -> CompetitorModel | None:
        """查找已存在的竞品记录

        精确匹配: brand + model + market（忽略大小写和空格）

        Args:
            db: 数据库会话
            brand: 品牌
            model: 型号
            market: 目标市场

        Returns:
            匹配的 CompetitorModel 或 None
        """
        brand_norm = CompetitorMatcher._normalize(brand)
        model_norm = CompetitorMatcher._normalize(model)
        market_norm = CompetitorMatcher._normalize(market)

        return (
            db.query(CompetitorModel)
            .filter(
                func.replace(func.lower(CompetitorModel.brand), " ", "")
                == brand_norm,
                func.replace(func.lower(CompetitorModel.model), " ", "")
                == model_norm,
                func.replace(func.lower(CompetitorModel.market), " ", "")
                == market_norm,
            )
            .first()
        )

    # ── 去重判断 ──

    @staticmethod
    def is_duplicate(item: CompetitorItem, existing: CompetitorModel) -> bool:
        """判断是否重复

        规则:
        - 如果现有记录 source='manual' → 始终视为重复（不覆盖人工数据）
        - 如果新 confidence < 0.4 → 视为重复（太低，存为 draft）
        - 如果新 confidence >= 0.4 且现有 confidence 更低 → 不重复（可以更新）
        - 否则 → 重复

        Args:
            item: 新的竞品条目
            existing: 已存在的竞品记录

        Returns:
            True 表示重复（应跳过或存 draft），False 表示不重复（可以更新）
        """
        # 规则1: 不覆盖人工数据
        if existing.source == "manual":
            return True

        # 规则2: 置信度过低
        if item.confidence < 0.4:
            return True

        # 规则3: 新数据置信度更高时可以更新
        # 使用 getattr 兼容 CompetitorModel 可能尚无 confidence 字段的情况
        existing_confidence = getattr(existing, "confidence", None)
        if item.confidence >= 0.4 and (
            existing_confidence is None or item.confidence > existing_confidence
        ):
            return False

        # 规则4: 否则视为重复
        return True

    # ── 差异计算 ──

    @staticmethod
    def compute_diff(
        item: CompetitorItem, existing: CompetitorModel
    ) -> dict[str, dict[str, Any]]:
        """计算新旧差异

        将 item.raw_params（经字段映射后）与 existing 做逐字段对比，
        返回有变化的字段及其新旧值。

        Args:
            item: 新的竞品条目
            existing: 已存在的竞品记录

        Returns:
            {field_name: {"old": old_val, "new": new_val}, ...}
            只包含有变化的字段
        """
        # 延迟导入避免循环引用
        from .saver import CompetitorSaver  # noqa: F811

        # 将 raw_params 映射到模型字段名
        mapped = CompetitorSaver._build_competitor_dict(item)

        diff: dict[str, dict[str, Any]] = {}

        for field, new_val in mapped.items():
            if not hasattr(existing, field):
                continue
            old_val = getattr(existing, field)

            # 跳过 None ↔ None 的无意义差异
            if old_val is None and new_val is None:
                continue

            # 值不同则记录
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}

        return diff

    # ── 更新判定 ──

    @staticmethod
    def should_update(item: CompetitorItem, existing: CompetitorModel) -> bool:
        """判断是否应该更新

        规则:
        - 新数据的 confidence >= 0.6 且 相比现有有更多的非空字段 → 更新
        - 或者核心字段（制冷量/能效比）有变化且新数据更可信 → 更新
        - 从不覆盖 source='manual' 的记录 → 不更新

        Args:
            item: 新的竞品条目
            existing: 已存在的竞品记录

        Returns:
            True 表示应该更新，False 表示不应更新
        """
        # 从不覆盖手动录入的数据
        if existing.source == "manual":
            return False

        # 置信度太低不更新
        if item.confidence < 0.4:
            return False

        from .saver import CompetitorSaver  # noqa: F811

        mapped = CompetitorSaver._build_competitor_dict(item)

        # 计算新数据中非空字段数量（仅统计模型存在的字段）
        new_non_null = 0
        for field, val in mapped.items():
            if hasattr(existing, field) and val is not None:
                new_non_null += 1

        # 计算现有记录中非空字段数量（仅统计 mapped 中出现的字段）
        existing_non_null = 0
        for field in mapped:
            if hasattr(existing, field) and getattr(existing, field) is not None:
                existing_non_null += 1

        # 规则1: confidence >= 0.6 且有更多非空字段 → 更新
        if item.confidence >= 0.6 and new_non_null > existing_non_null:
            return True

        # 规则2: 核心字段有变化且新数据更可信 → 更新
        existing_confidence = getattr(existing, "confidence", None)
        if existing_confidence is None or item.confidence > existing_confidence:
            for field in CompetitorMatcher.CORE_FIELDS:
                if field in mapped and mapped[field] is not None:
                    existing_val = getattr(existing, field, None)
                    if existing_val is None or existing_val != mapped[field]:
                        return True

        return False
