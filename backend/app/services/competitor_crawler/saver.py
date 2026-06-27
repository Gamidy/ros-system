"""竞品入库保存器 — 新增、更新、版本快照"""

import copy
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.competitor import CompetitorModel, COMPETITOR_SOURCE_AUTO
from app.models.competitor_version import CompetitorVersion
from .base import CompetitorItem

logger = logging.getLogger(__name__)


class CompetitorSaver:
    """竞品入库保存器

    负责将 CompetitorItem 写入数据库（新增或更新），
    并在更新时创建版本快照记录。
    """

    # raw_params 键名 → CompetitorModel 字段名映射
    # 处理 camelCase / snake_case / 同义字段名
    FIELD_MAP: dict[str, str] = {
        # ── 直通映射（snake_case → snake_case） ──
        "cooling_capacity_w": "cooling_capacity_w",
        "heating_capacity_w": "heating_capacity_w",
        "energy_rating": "energy_rating",
        "eer": "eer",
        "cspf": "cspf",
        "noise_indoor_db": "noise_indoor_db",
        "noise_outdoor_db": "noise_outdoor_db",
        "airflow_m3h": "airflow_m3h",
        "cooling_capacity": "cooling_capacity",
        "cooling_w": "cooling_w",
        "heating_w": "heating_w",
        "product_type": "product_type",
        "launch_year": "launch_year",
        "factory_price": "factory_price",
        "indoor_size_mm": "indoor_size_mm",
        "outdoor_size_mm": "outdoor_size_mm",
        "notes": "notes",
        # ── camelCase 变体 ──
        "coolingCapacityW": "cooling_capacity_w",
        "heatingCapacityW": "heating_capacity_w",
        "energyRating": "energy_rating",
        "coolingW": "cooling_w",
        "heatingW": "heating_w",
        "noiseIndoorDb": "noise_indoor_db",
        "noiseOutdoorDb": "noise_outdoor_db",
        "airflowM3h": "airflow_m3h",
        "productType": "product_type",
        "launchYear": "launch_year",
        "factoryPrice": "factory_price",
        "indoorSizeMm": "indoor_size_mm",
        "outdoorSizeMm": "outdoor_size_mm",
        "sourceUrl": "source_url",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── 新增 ──

    def save_new(self, item: CompetitorItem) -> CompetitorModel:
        """创建新竞品记录

        - source = COMPETITOR_SOURCE_AUTO ('auto')
        - 如果 confidence < 0.4，将参数存入 notes/draft 字段
        - 从 CompetitorItem.raw_params 映射到 CompetitorModel 字段
        - 返回创建的 CompetitorModel

        Args:
            item: 竞品条目

        Returns:
            新创建的 CompetitorModel 实例
        """
        record_dict = self._build_competitor_dict(item)

        # 补充必填字段
        record_dict["brand"] = item.brand
        record_dict["model"] = item.model
        record_dict["market"] = item.market
        record_dict["source"] = COMPETITOR_SOURCE_AUTO
        record_dict["source_url"] = item.source_url

        # 低置信度存入 notes 标记为 draft
        if item.confidence < 0.4:
            notes = record_dict.get("notes") or ""
            draft_info = (
                f"[DRAFT] confidence={item.confidence:.2f}"
            )
            if item.raw_text:
                # 截断过长文本
                raw_preview = item.raw_text[:500].replace("\n", " ")
                draft_info += f" | raw_text={raw_preview}"
            if notes:
                notes = draft_info + "\n" + notes
            else:
                notes = draft_info
            record_dict["notes"] = notes

        record = CompetitorModel(**record_dict)
        self.db.add(record)
        self.db.flush()

        logger.info(
            "新增竞品: brand=%s model=%s market=%s confidence=%.2f",
            item.brand, item.model, item.market, item.confidence,
        )

        return record

    # ── 更新 ──

    def update_existing(
        self,
        item: CompetitorItem,
        existing: CompetitorModel,
    ) -> CompetitorModel:
        """更新现有记录 + 写入版本快照

        - 计算 diff
        - 如果有变更，创建 CompetitorVersion 快照记录
        - 更新字段
        - copy.deepcopy() JSON 字段再赋值（见 vibe-coding 原则36）
        - 返回更新后的 CompetitorModel

        Args:
            item: 新的竞品条目
            existing: 已存在的竞品记录

        Returns:
            更新后的 CompetitorModel 实例（same object as existing）
        """
        from .matcher import CompetitorMatcher  # noqa: F811

        # 计算差异
        diff = CompetitorMatcher.compute_diff(item, existing)

        if not diff:
            logger.debug(
                "无变更跳过: brand=%s model=%s",
                item.brand, item.model,
            )
            return existing

        # 保存版本快照（变更前）
        self.save_version_snapshot(existing, diff)

        # 更新各字段
        mapped = self._build_competitor_dict(item)
        for field, new_val in mapped.items():
            if field in diff and hasattr(existing, field):
                # 原则36: deepcopy JSON 字段再赋值，避免 SQLAlchemy dirty flag 问题
                if isinstance(new_val, (dict, list)):
                    setattr(existing, field, copy.deepcopy(new_val))
                else:
                    setattr(existing, field, new_val)

        # 更新来源信息
        if item.source_url:
            existing.source_url = item.source_url

        self.db.flush()

        logger.info(
            "更新竞品: brand=%s model=%s fields=%s",
            item.brand, item.model, list(diff.keys()),
        )

        return existing

    # ── 字段映射 ──

    @staticmethod
    def _build_competitor_dict(item: CompetitorItem) -> dict[str, Any]:
        """将 CompetitorItem.raw_params 映射到 CompetitorModel 的字段名

        做字段名转换: raw_params 可能用 camelCase 或不同命名。
        字段名通不过 FIELD_MAP 的将原样保留（兼容上层已使用正确字段名的情况）。

        Args:
            item: 竞品条目

        Returns:
            字段名→值的字典，可用于构造/更新 CompetitorModel
        """
        result: dict[str, Any] = {}

        for key, value in item.raw_params.items():
            # 优先通过 FIELD_MAP 转换
            mapped_key = CompetitorSaver.FIELD_MAP.get(key)
            if mapped_key:
                result[mapped_key] = value
                continue

            # 未映射的字段 — 原样保留（信任上层已使用正确字段名或为扩展字段）
            # 排除一些内部字段
            if key in ("confidence", "raw_text", "source_url", "brand", "model", "market"):
                continue
            result[key] = value

        return result

    # ── 版本快照 ──

    def save_version_snapshot(
        self,
        competitor: CompetitorModel,
        changed_fields: dict[str, dict[str, Any]],
    ) -> CompetitorVersion:
        """创建版本快照记录

        - changed_by = 'system' (自动采集)
        - snapshot_data = 快照时的完整数据
        - 使用 deepcopy 避免 SQLAlchemy dirty flag 问题

        Args:
            competitor: 快照时的竞品记录（变更前状态）
            changed_fields: 变更字段详情 {field: {old: val, new: val}}

        Returns:
            创建的 CompetitorVersion 实例
        """
        # 构建完整的快照数据
        # deepcopy 避免 SQLAlchemy dirty flag: 直接读取属性值
        snapshot: dict[str, Any] = {}
        for column in CompetitorModel.__table__.columns:
            col_name = column.name
            val = getattr(competitor, col_name, None)
            if isinstance(val, (dict, list)):
                snapshot[col_name] = copy.deepcopy(val)
            else:
                snapshot[col_name] = val

        version = CompetitorVersion(
            competitor_id=competitor.id,
            changed_fields=copy.deepcopy(changed_fields),
            snapshot_data=snapshot,
            changed_by="system",
        )
        self.db.add(version)
        self.db.flush()

        return version
