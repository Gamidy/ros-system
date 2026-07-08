"""竞品 AI 解析服务 — 包装 LLMParamExtractor 并提供结构化转换

职责：
1. 接收上游传入的原始文本 / 文件内容
2. 调用 LLMParamExtractor.extract() 进行 AI 提取
3. 将提取结果转换为 CompetitorExtraction 格式
4. 支持批量处理（一页文本可能包含多条产品信息）
"""
import asyncio
import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.competitor_crawler.llm_extractor import LLMParamExtractor
from app.schemas.ai_competitor_import import (
    AIExtractedField,
    CompetitorExtraction,
)

logger = logging.getLogger(__name__)

# ── LLMParamExtractor 返回字段到 CompetitorExtraction 字段的映射 ──
# key: LLMParamExtractor 返回的字段名
# value: CompetitorExtraction 中对应的字段名
FIELD_MAPPING: dict[str, str] = {
    "brand": "brand",
    "model": "model",
    "product_type": "product_type",
    "cooling_capacity_w": "capacity_kw",    # LLM 返回 W，转储为 kW
    "heating_capacity_w": "heating_capacity_btu",
    "eer": "eer",
    "cspf": "seer",                          # CSPF ≈ SEER
    "noise_indoor_db": "indoor_noise_db",
    "noise_outdoor_db": "outdoor_noise_db",
    "cooling_w": "power_input_w",            # 制冷功率 → power_input_w
    "heating_w": "power_input_w",            # 制热功率（兜底）
    "energy_rating": "energy_label",
    "factory_price": "price",
}


def _build_extracted_field(
    value: Any,
    overall_confidence: float,
) -> AIExtractedField:
    """构建 AIExtractedField

    Args:
        value: 提取到的值（任意类型，会被转为 str）
        overall_confidence: 整体置信度，作为字段置信度

    Returns:
        AIExtractedField 实例
    """
    if value is None:
        return AIExtractedField(value=None, confidence=0.0)
    return AIExtractedField(
        value=str(value),
        confidence=overall_confidence,
    )


def _llm_result_to_extraction(
    llm_result: dict[str, Any],
) -> CompetitorExtraction:
    """将 LLMParamExtractor 的 flat dict 结果转换为 CompetitorExtraction

    Args:
        llm_result: LLMParamExtractor.extract() 返回的 dict

    Returns:
        CompetitorExtraction 结构化实例
    """
    overall_confidence = float(llm_result.get("confidence", 0.0))
    notes: list[str] = []

    # 从 LLM 结果构建每个字段
    extraction = CompetitorExtraction(
        brand=_build_extracted_field(
            llm_result.get("brand"), overall_confidence,
        ),
        model=_build_extracted_field(
            llm_result.get("model"), overall_confidence,
        ),
        product_type=_build_extracted_field(
            llm_result.get("product_type"), overall_confidence,
        ),
        overall_confidence=overall_confidence,
    )

    # ── 冷量换算 (W → BTU) ──
    cooling_w = llm_result.get("cooling_capacity_w")
    if cooling_w is not None:
        try:
            cw = int(cooling_w)
            extraction.capacity_kw = AIExtractedField(
                value=str(round(cw / 1000, 2)),
                confidence=overall_confidence,
            )
            # BTU = W * 3.412
            extraction.capacity_btu = AIExtractedField(
                value=str(round(cw * 3.412)),
                confidence=overall_confidence,
            )
        except (ValueError, TypeError):
            notes.append("冷量(W)值无法解析")

    # ── 制热量换算 (W → BTU) ──
    heating_w = llm_result.get("heating_capacity_w")
    if heating_w is not None:
        try:
            hw = int(heating_w)
            extraction.heating_capacity_btu = AIExtractedField(
                value=str(round(hw * 3.412)),
                confidence=overall_confidence,
            )
        except (ValueError, TypeError):
            notes.append("制热量(W)值无法解析")

    # ── EER ──
    eer = llm_result.get("eer")
    if eer is not None:
        extraction.eer = AIExtractedField(
            value=str(eer), confidence=overall_confidence,
        )

    # ── SEER (优先使用 seer 字段，兼容 cspf) ──
    seer_val = llm_result.get("seer") or llm_result.get("cspf")
    if seer_val is not None:
        extraction.seer = AIExtractedField(
            value=str(seer_val), confidence=overall_confidence,
        )

    # ── CSPF → SEER (兼容旧字段名) ──
    cspf = llm_result.get("cspf")
    if cspf is not None and extraction.seer.value is None:
        extraction.seer = AIExtractedField(
            value=str(cspf), confidence=overall_confidence,
        )

    # ── 室内噪音 ──
    noise_in = llm_result.get("noise_indoor_db")
    if noise_in is not None:
        extraction.indoor_noise_db = AIExtractedField(
            value=str(noise_in), confidence=overall_confidence,
        )

    # ── 室外噪音 ──
    noise_out = llm_result.get("noise_outdoor_db")
    if noise_out is not None:
        extraction.outdoor_noise_db = AIExtractedField(
            value=str(noise_out), confidence=overall_confidence,
        )

    # ── 功率输入 (cooling_w 优先) ──
    cooling_w_val = llm_result.get("cooling_w")
    heating_w_val = llm_result.get("heating_w")
    if cooling_w_val is not None:
        extraction.power_input_w = AIExtractedField(
            value=str(cooling_w_val), confidence=overall_confidence,
        )
    elif heating_w_val is not None:
        extraction.power_input_w = AIExtractedField(
            value=str(heating_w_val), confidence=overall_confidence,
        )

    # ── 能效等级 ──
    energy_rating = llm_result.get("energy_rating")
    if energy_rating is not None:
        extraction.energy_label = AIExtractedField(
            value=str(energy_rating), confidence=overall_confidence,
        )

    # ── 价格 ──
    price = llm_result.get("factory_price")
    if price is not None:
        extraction.price = AIExtractedField(
            value=str(price), confidence=overall_confidence,
        )

    # ── 冷媒类型 ──
    refrigerant = llm_result.get("refrigerant")
    if refrigerant is not None:
        extraction.refrigerant = AIExtractedField(
            value=str(refrigerant), confidence=overall_confidence,
        )

    if notes:
        extraction.extraction_notes = "; ".join(notes)

    return extraction


class CompetitorAIParser:
    """竞品 AI 解析服务

    包装 LLMParamExtractor，对外提供结构化转换接口。
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    async def parse_text(
        self,
        raw_text: str,
        market_code: str,
        brand: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> CompetitorExtraction:
        """解析单段文本，返回结构化的竞品提取结果

        Args:
            raw_text:  非结构化产品文本
            market_code: 目标市场代码（如 "VN", "US"）
            brand:      品牌名称（兜底用）
            provider:   AI 供应商
            model:      AI 模型名
            api_key:    API 密钥
            api_base:   API Base URL

        Returns:
            CompetitorExtraction 实例
        """
        extractor = LLMParamExtractor(db=self.db)
        result = await extractor.extract(
            raw_text=raw_text,
            market=market_code,
            brand=brand,
            provider=provider,
            model=model,
            api_key=api_key,
            api_base=api_base,
        )
        return _llm_result_to_extraction(result)

    async def parse_text_multi(
        self,
        raw_text: str,
        market_code: str,
        default_brand: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> list[CompetitorExtraction]:
        """解析包含多个产品的文本，返回所有提取结果

        策略：
        1. 如果文本包含 "=== Product N:" 标记，按标记分割为独立产品段落
        2. 对每个段落并发调用 extract() 逐个提取（更快更准）
        3. 无标记时回退到 extract_all() 一次调用

        Args:
            raw_text:     包含多个产品的文本
            market_code:  目标市场代码
            default_brand: 默认品牌
            provider:     AI 供应商
            model:        AI 模型名
            api_key:      API 密钥
            api_base:     API Base URL

        Returns:
            list[CompetitorExtraction]: 所有产品提取结果
        """
        # ── 检查是否有 "=== Product N:" 分割标记 ──
        product_blocks = re.split(
            r"=== Product \d+:.*?===\n?",
            raw_text,
        )
        # 过滤掉空块和过短的块
        product_blocks = [
            b.strip() for b in product_blocks
            if b.strip() and len(b.strip()) > 20
        ]

        if len(product_blocks) <= 1:
            # 无分割标记 → 使用 extract_all 一次性调用
            extractor = LLMParamExtractor(db=self.db)
            results = await extractor.extract_all(
                raw_text=raw_text,
                market=market_code,
                brand=default_brand,
                provider=provider,
                model=model,
                api_key=api_key,
                api_base=api_base,
            )
            return [_llm_result_to_extraction(r) for r in results]

        # ── 有分割标记 → 并发提取每个产品 ──
        logger.info("parse_text_multi: split into %d product blocks", len(product_blocks))
        extractor = LLMParamExtractor(db=self.db)

        async def _extract_one(text: str) -> CompetitorExtraction:
            """提取单个产品"""
            try:
                result = await extractor.extract(
                    raw_text=text,
                    market=market_code,
                    brand=default_brand,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                )
                return _llm_result_to_extraction(result)
            except Exception as exc:
                logger.warning("Single product extraction failed: %s", exc)
                return CompetitorExtraction(
                    brand=AIExtractedField(value=None, confidence=0.0),
                    model=AIExtractedField(value=None, confidence=0.0),
                    product_type=AIExtractedField(value=None, confidence=0.0),
                    overall_confidence=0.0,
                    extraction_notes=f"解析失败: {exc}",
                )

        # 并发执行（最多 5 个并发，避免 API 限流）
        semaphore = asyncio.Semaphore(5)

        async def _with_semaphore(text: str) -> CompetitorExtraction:
            async with semaphore:
                return await _extract_one(text)

        tasks = [_with_semaphore(block) for block in product_blocks]
        extractions: list[CompetitorExtraction | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        result: list[CompetitorExtraction] = []
        for i, ext in enumerate(extractions):
            if isinstance(ext, Exception):
                logger.warning("Product %d extraction raised: %s", i, ext)
                result.append(CompetitorExtraction(
                    brand=AIExtractedField(value=None, confidence=0.0),
                    model=AIExtractedField(value=None, confidence=0.0),
                    product_type=AIExtractedField(value=None, confidence=0.0),
                    overall_confidence=0.0,
                    extraction_notes=f"并发解析异常: {ext}",
                ))
            else:
                result.append(ext)

        logger.info("parse_text_multi: %d/%d products extracted", 
                     sum(1 for r in result if r.overall_confidence > 0), len(result))
        return result

    async def parse_text_batch(
        self,
        texts: list[str],
        market_code: str,
        default_brand: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> list[CompetitorExtraction]:
        """批量解析多段文本

        对每段文本分别调用 LLMParamExtractor，返回结果列表。

        Args:
            texts:         多段产品文本
            market_code:   目标市场代码
            default_brand: 默认品牌（兜底）
            provider:      AI 供应商
            model:         AI 模型名
            api_key:       API 密钥
            api_base:      API Base URL

        Returns:
            list[CompetitorExtraction]
        """
        extractor = LLMParamExtractor(db=self.db)
        extractions: list[CompetitorExtraction] = []
        for idx, text in enumerate(texts):
            try:
                result = await extractor.extract(
                    raw_text=text,
                    market=market_code,
                    brand=default_brand,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                )
                extractions.append(_llm_result_to_extraction(result))
            except Exception as exc:
                logger.warning("批量解析第 %d 段失败: %s", idx, exc)
                # 返回一个空提取结果，不阻断后续
                extractions.append(
                    CompetitorExtraction(
                        brand=AIExtractedField(value=None, confidence=0.0),
                        model=AIExtractedField(value=None, confidence=0.0),
                        product_type=AIExtractedField(value=None, confidence=0.0),
                        overall_confidence=0.0,
                        extraction_notes=f"解析失败: {exc}",
                    )
                )
        return extractions
