"""
LLM 参数智能解析引擎 — LLMParamExtractor

使用 LLM (大语言模型) 从非结构化文本中提取空调参数，
自动降级到 RegexParamExtractor（正则方案）作为后备。

设计原则：
  - 复用项目已有的 ai_chat() 统一接口
  - LLM 提取 → UnitNormalizer 校验归一化 → 置信度评分
  - 失败时自动降级，不抛异常
  - 所有方法可单独测试
"""

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai import ai_chat
from app.models.ai_config import AIConfig

from .regex_extractor import RegexParamExtractor
from .unit_normalizer import UnitNormalizer

logger = logging.getLogger(__name__)

# ── LLM 输出 JSON Schema ─────────────────────────────────────────────
# key → type hint 用于 prompt 构建
OUTPUT_SCHEMA: dict[str, str] = {
    "brand": "str",
    "model": "str",
    "product_type": "str",
    "cooling_capacity_w": "int | null",
    "heating_capacity_w": "int | null",
    "energy_rating": "str | null",
    "cooling_w": "int | null",
    "heating_w": "int | null",
    "eer": "float | null",
    "seer": "float | null",           # SEER (EU) / CSPF (SE Asia) / ISEER (India)
    "cspf": "float | null",           # same as SEER for SE Asia markets
    "noise_indoor_db": "float | null",
    "noise_outdoor_db": "float | null",
    "airflow_m3h": "float | null",
    "refrigerant": "str | null",      # 冷媒类型 (R32, R410A, R290, etc.)
    "indoor_size_mm": "str | null",
    "outdoor_size_mm": "str | null",
    "factory_price": "str | null",
    "launch_year": "int | null",
    "confidence": "float",
}

# 核心字段（置信度计算中的权重最高）
CORE_FIELDS: set[str] = {"cooling_capacity_w", "eer", "noise_indoor_db"}

# 全部可能字段数（不含 confidence）
TOTAL_FIELDS: int = len(OUTPUT_SCHEMA) - 1  # 19


class LLMParamExtractor:
    """LLM 参数智能解析引擎

    主流程:
        1. 优先使用 LLM 提取参数（从 ai_config 表读取配置或显式传入）
        2. 解析 LLM 返回的 JSON
        3. 用 UnitNormalizer 二次校验 / 归一化数值
        4. 计算置信度分数
        5. 若 LLM 失败或 DB 无可用配置，降级到 RegexParamExtractor
    """

    def __init__(self, db: Session | None = None):
        """初始化

        Args:
            db: 数据库 Session（用于读取 ai_config 和写入调用日志）
        """
        self.db = db

    # ═══════════════════════════════════════════════════════════════════
    # 公开方法
    # ═══════════════════════════════════════════════════════════════════

    async def extract(
        self,
        raw_text: str,
        market: str,
        brand: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> dict[str, Any]:
        """从非结构化文本中提取空调参数

        流程:
        1. 如果没有显式传 provider / model / api_key，从 ai_config DB 表读取
        2. 构建 system prompt（含 JSON Schema 约束 + 示例）
        3. 调用 ai_chat()
        4. 解析 LLM 返回的 JSON
        5. 用 UnitNormalizer 二次校验/修正数值
        6. 计算 confidence 分数
        7. 如果 LLM 失败或返回非 JSON，降级到 RegexParamExtractor.extract_all()
        8. 返回 dict

        Args:
            raw_text:  非结构化文本（如产品页面 HTML / 描述）
            market:    目标市场代码（如 VN / US / SA）
            brand:     品牌名称（可选；LLM 提取失败时用此值兜底）
            provider:  AI 供应商名称（如 "deepseek"），可选
            model:     模型名称（如 "deepseek-chat"），可选
            api_key:   API 密钥明文，可选
            api_base:  API Base URL，可选

        Returns:
            dict: 提取的参数，格式与 CompetitorModel 字段兼容，包含 confidence
        """
        # ── 1. 获取 LLM 配置 ──
        if not all([provider, model, api_key]):
            config = self._load_ai_config()
            if config is not None:
                provider = provider or str(config.provider)
                model = model or str(config.model)
                api_key = api_key or str(config.get_api_key())
                api_base = api_base or (str(config.api_base) if config.api_base is not None else None)

        # ── 2. 调用 LLM ──
        llm_result: dict[str, Any] | None = None

        if provider and model and api_key:
            try:
                llm_result = await self._call_llm(
                    raw_text=raw_text,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                )
            except Exception as exc:
                logger.warning("LLM extraction error: %s", exc, exc_info=True)

        # ── 3. 校验和归一化 ──
        if llm_result is not None:
            llm_result = self._validate_and_normalize(llm_result)
            llm_result["confidence"] = self._calculate_confidence(llm_result)
            # 用户传入的 brand 参数优先于 AI 提取的品牌（用户已知制造商）
            if brand:
                llm_result["brand"] = brand
            llm_result.setdefault("market", market)
            return llm_result

        # ── 4. 降级到正则方案 ──
        logger.info(
            "LLM extraction unavailable or failed, falling back to RegexParamExtractor"
        )
        return self._fallback_to_regex(raw_text, market, brand)

    async def extract_all(
        self,
        raw_text: str,
        market: str,
        brand: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> list[dict[str, Any]]:
        """从文本中提取所有产品参数（支持多产品）

        与 extract() 不同，此方法会：
        - 使用提示 LLM 输出 JSON 数组（多产品）
        - 返回所有产品的结构化数据

        Args:
            同 extract()

        Returns:
            list[dict]: 所有提取的产品参数列表
        """
        # ── 1. 获取 LLM 配置 ──
        if not all([provider, model, api_key]):
            config = self._load_ai_config()
            if config is not None:
                provider = provider or str(config.provider)
                model = model or str(config.model)
                api_key = api_key or str(config.get_api_key())
                api_base = api_base or (str(config.api_base) if config.api_base is not None else None)

        # ── 2. 直接调用 LLM（跳过 _call_llm，后者只返回单产品）──
        if provider and model and api_key:
            try:
                # 使用多产品专用 system prompt（允许提取全部产品）
                system_prompt = self._build_system_prompt(multi_product=True)
                response = await ai_chat(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    api_base=api_base,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                    log_to_db=True,
                    db_session=self.db,
                )

                if response.success:
                    parsed = self._parse_llm_response(response.text)
                    if isinstance(parsed, list):
                        # 多产品数组
                        results = []
                        for item in parsed:
                            if isinstance(item, dict):
                                validated = self._validate_and_normalize(item)
                                validated["confidence"] = self._calculate_confidence(validated)
                                if brand:
                                    validated["brand"] = brand
                                validated.setdefault("market", market)
                                results.append(validated)
                        if results:
                            logger.info("extract_all: %d products extracted", len(results))
                            return results
                    elif isinstance(parsed, dict):
                        # 单产品 → 包装为列表
                        validated = self._validate_and_normalize(parsed)
                        validated["confidence"] = self._calculate_confidence(validated)
                        if brand:
                            validated["brand"] = brand
                        validated.setdefault("market", market)
                        return [validated]
            except Exception as exc:
                logger.warning("LLM extract_all error: %s", exc, exc_info=True)

        # ── 降级到单产品提取 ──
        logger.info("extract_all: falling back to single extract")
        single = self._fallback_to_regex(raw_text, market, brand)
        return [single]

    # ═══════════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════════

    def _load_ai_config(self) -> AIConfig | None:
        """从数据库读取已启用的第一条 AI 供应商配置

        Returns:
            AIConfig | None: 配置对象，无可用配置或 DB 不可用时返回 None
        """
        if self.db is None:
            return None
        try:
            return (
                self.db.query(AIConfig)
                .filter(AIConfig.enabled == True)
                .first()
            )
        except Exception as exc:
            logger.warning("Failed to load AI config from DB: %s", exc)
            return None

    async def _call_llm(
        self,
        raw_text: str,
        provider: str,
        model: str,
        api_key: str,
        api_base: str | None,
    ) -> dict[str, Any] | None:
        """调用 LLM 并解析返回的 JSON

        Args:
            raw_text: 原始产品文本
            provider: AI 供应商名称
            model:    模型名称
            api_key:  API 密钥（明文）
            api_base: API Base URL（可选）

        Returns:
            dict | None: 解析后的参数字典，失败返回 None
        """
        system_prompt = self._build_system_prompt()

        response = await ai_chat(
            provider=provider,
            model=model,
            api_key=api_key,
            api_base=api_base,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            temperature=0.1,
            max_tokens=4096,
            log_to_db=True,
            db_session=self.db,
        )

        if not response.success:
            logger.warning("LLM call failed: %s", response.error)
            return None

        parsed = self._parse_llm_response(response.text)
        if parsed is None:
            logger.warning("Failed to parse LLM response as JSON")
            return None

        # 如果 LLM 返回了数组（多产品模式），只取第一个
        if isinstance(parsed, list):
            if parsed:
                logger.info("LLM returned %d products, using first one", len(parsed))
                return parsed[0]
            logger.warning("LLM returned empty array")
            return None

        return parsed

    def _build_system_prompt(self, multi_product: bool = False) -> str:
        """构建 system prompt

        包含:
        - 角色定义（专业空调参数提取器）
        - JSON 严格输出约束
        - 单位转换要求
        - 完整输出 Schema
        - 表格/对比表输入处理说明
        - 多产品提取示例

        Args:
            multi_product: True 时提示 LLM 提取所有产品返回 JSON 数组

        Returns:
            str: system prompt 文本
        """
        schema_lines = "\n".join(
            f'    "{key}": {type_hint},'
            for key, type_hint in OUTPUT_SCHEMA.items()
        )

        # 多产品模式下覆盖输出规则
        output_rules = ""
        if multi_product:
            output_rules = """
## 输出格式（多产品模式）
- **总是输出 JSON 数组** `[{...}, {...}, ...]`，即使只有 1 个产品
- 数组中的每个元素代表一个产品
- 不要包含任何说明文字、Markdown 包裹或代码块标记"""
        else:
            output_rules = """
## 输出格式（单产品模式）
- **如果输入文本包含 1 个产品：输出单个 JSON 对象** `{...}`
- **如果输入文本包含 2 个或更多产品：输出 JSON 数组** `[{...}, {...}, ...]`
- 不要包含任何说明文字、Markdown 包裹或代码块标记"""

        return f"""你是一个专业的家用分体式空调(AC Split-type)参数提取器。

## 核心任务
从用户提供的**任何格式**的文本中提取空调参数，输出严格 JSON。

## 重要：输出格式
{output_rules}

## 输入可能格式
1. **段落描述**：产品介绍的连续文字（如网页描述、产品目录）
2. **表格/对比表**：多行多列的数据表格（如 Excel/PDF 对比表每一行是一条产品）
3. **半结构化**：混合了表头和数据的文本（如 HTML 表格提取结果）
4. **列式矩阵**：每个产品参数占一行，参数名→值横跨多列。格式为"=== Product N: Series X Model Y ==="开头，后跟"参数名: 值"格式的每行一个参数。系统已经把每个产品单独分段。

## 提取规则
1. 输出必须是**严格 JSON 对象**，只输出 JSON，不要任何说明文字、Markdown 包裹或代码块标记。
2. 所有数值字段必须是正确的类型（int / float / str / null），不要用字符串表示数字。
3. **如果文本中明确不包含某个字段，设为 null，不要假设或编造值。**
{f"4. **如果输入是表格/对比表（包含多行数据且每行是不同的产品），只提取表格中的第一条产品数据。** 系统会为每一行调用一次提取。" if not multi_product else "4. **提取输入文本中所有能找到的产品。** 每个产品输出数组中的一个元素。"}
5. **如果输入是段落描述（单条产品），提取该产品的所有可识别参数。**

## 单位转换要求（重要！）
- 制冷量/制热量必须用 **W（瓦特）**
  - 匹数 → W：1匹≈2500W，1.5匹≈3500W，2匹≈5000W，2.5匹≈6000W，3匹≈7200W
  - BTU/h → W：1 BTU/h ≈ 0.293W（如 9000BTU≈2637W，12000BTU≈3516W）
  - kW → W：2.8kW → 2800W
  - 注意：如果输入中已包含 "制冷量T1 (W)" 这样的 W 单位列，直接用，不要再转换
- 噪音用 dB（去括号尾注，如"38dB(A)" → 38.0）
- 风量用 m³/h
- 价格：保留原字符串，含货币符号（如"$599", "฿15,900", "₫12,500,000"）

## 置信度评分指南
- 0.9-1.0：文本清晰包含准确数值，无歧义
- 0.6-0.8：文本包含数值但有轻微歧义（如单位推断、近似值）
- 0.3-0.5：数值不明确，做了合理推断
- 0.0-0.2：几乎无有效数据可提取

## 输出 JSON Schema
{{
{schema_lines}
}}

## 示例1：段落描述
输入：
"AUX AS-12HR4SVETG 分体壁挂式空调，制冷量 1.5匹(3500W)，制热量 3800W，EER 3.21，室内噪音 38dB(A)，室外噪音 52dB，风量 550m³/h，R32 冷媒，220V/50Hz，能效 1 级，净重 12kg"

输出：
{{
    "brand": "AUX",
    "model": "AS-12HR4SVETG",
    "product_type": "split wall-mounted",
    "cooling_capacity_w": 3500,
    "heating_capacity_w": 3800,
    "energy_rating": "1级",
    "cooling_w": null,
    "heating_w": null,
    "eer": 3.21,
    "seer": null,
    "cspf": null,
    "noise_indoor_db": 38.0,
    "noise_outdoor_db": 52.0,
    "airflow_m3h": 550.0,
    "refrigerant": "R32",
    "indoor_size_mm": null,
    "outdoor_size_mm": null,
    "factory_price": null,
    "launch_year": null,
    "confidence": 0.95
}}

## 示例2：表格输入（一条产品行）
输入：
"格力	KFR-35GW	3500W	3.21	38dB	52dB	R32	1级	$599"

输出：
{{
    "brand": "格力",
    "model": "KFR-35GW",
    "product_type": "split wall-mounted",
    "cooling_capacity_w": 3500,
    "heating_capacity_w": null,
    "energy_rating": "1级",
    "cooling_w": null,
    "heating_w": null,
    "eer": 3.21,
    "seer": null,
    "cspf": null,
    "noise_indoor_db": 38.0,
    "noise_outdoor_db": 52.0,
    "airflow_m3h": null,
    "refrigerant": "R32",
    "indoor_size_mm": null,
    "outdoor_size_mm": null,
    "factory_price": "$599",
    "launch_year": null,
    "confidence": 0.9
}}

请严格按 JSON 输出，不要包含任何其他内容。"""

    @staticmethod
    def _parse_llm_response(text: str) -> dict[str, Any] | list[dict[str, Any]] | None:
        """解析 LLM 返回的文本为 dict 或 list[dict]

        支持：
        - 单个 JSON 对象: {...}
        - JSON 数组: [{...}, {...}]
        - ```json ... ``` 包裹的 JSON
        - 多个 JSON 对象（多产品输入）

        Args:
            text: LLM 返回的原始文本

        Returns:
            dict | list[dict] | None: 解析成功返回 dict 或 list，失败返回 None
        """
        if not text or not text.strip():
            return None

        text = text.strip()
        parsed = None

        # Strategy 1: 直接解析（处理单个对象或数组）
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                # 数组 → 返回列表
                return [p for p in parsed if isinstance(p, dict)]
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Strategy 2: ```json ... ``` 代码块
        json_block = re.search(
            r"```(?:json)\s*\n(.+?)\n```",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if json_block:
            try:
                parsed = json.loads(json_block.group(1).strip())
                if isinstance(parsed, list):
                    return [p for p in parsed if isinstance(p, dict)]
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Strategy 3: ``` ... ``` 代码块
        generic_block = re.search(
            r"```\s*\n(.+?)\n```",
            text,
            re.DOTALL,
        )
        if generic_block:
            try:
                parsed = json.loads(generic_block.group(1).strip())
                if isinstance(parsed, list):
                    return [p for p in parsed if isinstance(p, dict)]
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Strategy 4: 提取 { ... } JSON 对象
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # Strategy 5: 提取 [...] JSON 数组
        bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
        if bracket_match:
            try:
                parsed = json.loads(bracket_match.group(0))
                if isinstance(parsed, list):
                    return [p for p in parsed if isinstance(p, dict)]
            except json.JSONDecodeError:
                pass

        return None

    def _validate_and_normalize(self, data: dict) -> dict[str, Any]:
        """校验和归一化提取的参数

        对 LLM 提取的各项参数进行合理性校验与单位归一化：
        - 字符串字段：去空白、null 处理
        - 制冷量/制热量：int 范围 1000-30000，小数值按匹数换算
        - 功率：int 范围 50-10000
        - EER / CSPF：float 范围 1-10
        - 噪音：float 范围 10-80
        - 风量：float 范围 100-5000
        - 上市年份：int 范围 2000-2030
        - 超出合理范围的值设为 null

        Args:
            data: LLM 返回的原始提取结果

        Returns:
            dict: 校验归一化后的结果（仅含 OUTPUT_SCHEMA 中的字段）
        """
        result: dict[str, Any] = {}

        # ── 字符串字段 ──
        for field in (
            "brand",
            "model",
            "product_type",
            "energy_rating",
            "refrigerant",
            "indoor_size_mm",
            "outdoor_size_mm",
            "factory_price",
        ):
            val = data.get(field)
            if val is not None and isinstance(val, str) and val.strip():
                result[field] = val.strip()
            else:
                result[field] = None

        # ── 制冷量：int 1000-30000，小数值按匹数换算 ──
        result["cooling_capacity_w"] = self._normalize_capacity(
            data.get("cooling_capacity_w"), 1000, 30000
        )

        # ── 制热量：int 1000-30000，小数值按匹数换算 ──
        result["heating_capacity_w"] = self._normalize_capacity(
            data.get("heating_capacity_w"), 1000, 30000
        )

        # ── 功率：int 50-10000 ──
        for field in ("cooling_w", "heating_w"):
            val = data.get(field)
            if val is not None and isinstance(val, (int, float)):
                try:
                    ival = int(round(float(val)))
                    result[field] = ival if 50 <= ival <= 10000 else None
                except (ValueError, TypeError):
                    result[field] = None
            else:
                result[field] = None

        # ── EER：float 1-10 ──
        result["eer"] = self._normalize_float(data.get("eer"), 1.0, 10.0)

        # ── SEER / CSPF：float 1-15 (SEER EU可达10+) ──
        result["seer"] = self._normalize_float(data.get("seer"), 1.0, 15.0)
        result["cspf"] = self._normalize_float(data.get("cspf"), 1.0, 10.0)

        # ── 噪音：float 10-80 ──
        result["noise_indoor_db"] = self._normalize_float(
            data.get("noise_indoor_db"), 10.0, 80.0
        )
        result["noise_outdoor_db"] = self._normalize_float(
            data.get("noise_outdoor_db"), 10.0, 80.0
        )

        # ── 风量：float 100-5000 ──
        val = data.get("airflow_m3h")
        if val is not None and isinstance(val, (int, float)):
            try:
                fval = float(val)
                result["airflow_m3h"] = (
                    round(fval, 1) if 100.0 <= fval <= 5000.0 else None
                )
            except (ValueError, TypeError):
                result["airflow_m3h"] = None
        else:
            result["airflow_m3h"] = None

        # ── 上市年份：int 2000-2030 ──
        val = data.get("launch_year")
        if val is not None:
            try:
                y = int(val)
                result["launch_year"] = y if 2000 <= y <= 2030 else None
            except (ValueError, TypeError):
                result["launch_year"] = None
        else:
            result["launch_year"] = None

        return result

    # ── 数值归一化辅助方法 ─────────────────────────────────────────

    @staticmethod
    def _normalize_capacity(
        val: Any,
        min_val: int,
        max_val: int,
    ) -> int | None:
        """归一化容量数值（制冷量 / 制热量）

        处理策略：
        - 若值为 0.5-10 之间的小数，视为匹数，用 UnitNormalizer 换算为 W
        - 若值为 int/float，直接取整并检查范围
        - 若值为字符串，尝试用 UnitNormalizer 解析

        Args:
            val:     输入值
            min_val: 最小值（W）
            max_val: 最大值（W）

        Returns:
            int | None: 归一化后的 W 值，无效时返回 None
        """
        if val is None:
            return None

        # 数值类型
        if isinstance(val, (int, float)):
            try:
                fval = float(val)
                # 小数值 → 疑似匹数
                if 0.5 <= fval <= 10.0:
                    converted = UnitNormalizer._horsepower_to_watts(fval)
                    return converted
                # 正常 W 值
                ival = int(round(fval))
                return ival if min_val <= ival <= max_val else None
            except (ValueError, TypeError):
                pass

        # 字符串类型 → 用 UnitNormalizer 解析
        if isinstance(val, str) and val.strip():
            converted = UnitNormalizer.normalize_cooling_capacity(val.strip())
            if converted is not None and min_val <= converted <= max_val:
                return converted

        return None

    @staticmethod
    def _normalize_float(
        val: Any,
        min_val: float,
        max_val: float,
    ) -> float | None:
        """归一化浮点数值，确保在合理范围内

        Args:
            val:     输入值
            min_val: 最小值
            max_val: 最大值

        Returns:
            float | None: 归一化后的值，无效时返回 None
        """
        if val is None:
            return None
        try:
            fval = float(val)
            return round(fval, 2) if min_val <= fval <= max_val else None
        except (ValueError, TypeError):
            return None

    # ── 置信度计算 ───────────────────────────────────────────────

    def _calculate_confidence(self, data: dict) -> float:
        """计算提取结果的置信度 (0.0 ~ 1.0)

        计算公式：
          - 核心字段（cooling_capacity_w + eer + noise_indoor_db）提取比例 × 0.6
          - 全部字段（17 个，不含 confidence）提取比例 × 0.3
          - 数值合理性 × 0.1
          - 没有任何字段被提取时返回 0.0

        Args:
            data: 已校验归一化的参数字典

        Returns:
            float: 置信度 0.0 ~ 1.0
        """
        all_fields = set(OUTPUT_SCHEMA.keys()) - {"confidence"}
        non_null = sum(1 for f in all_fields if data.get(f) is not None)

        if non_null == 0:
            return 0.0

        # 核心字段得分（冷却量 + 能效比 + 噪音）
        core_extracted = sum(1 for f in CORE_FIELDS if data.get(f) is not None)
        core_score = (core_extracted / len(CORE_FIELDS)) * 0.6

        # 全部字段得分
        all_score = (non_null / len(all_fields)) * 0.3

        # 数值合理性得分
        reasonability_score = self._score_reasonability(data) * 0.1

        confidence = round(core_score + all_score + reasonability_score, 4)
        return min(confidence, 1.0)

    @staticmethod
    def _score_reasonability(data: dict) -> float:
        """评估提取数值的合理性 (0.0 ~ 1.0)

        检查各数值是否在经验合理范围内，而非仅不超出极端边界。

        Args:
            data: 参数字典

        Returns:
            float: 合理性得分
        """
        checks = 0
        passed = 0

        # 制冷量合理性（常见家用空调范围）
        cc = data.get("cooling_capacity_w")
        if cc is not None:
            checks += 1
            if 2000 <= cc <= 15000:
                passed += 1

        # EER 合理性（常见能效比范围）
        eer = data.get("eer")
        if eer is not None:
            checks += 1
            if 2.0 <= eer <= 8.0:
                passed += 1

        # 室内噪音合理性
        noise_in = data.get("noise_indoor_db")
        if noise_in is not None:
            checks += 1
            if 20.0 <= noise_in <= 60.0:
                passed += 1

        # 室外噪音合理性（一般比室内高）
        noise_out = data.get("noise_outdoor_db")
        if noise_out is not None:
            checks += 1
            if 40.0 <= noise_out <= 70.0:
                passed += 1

        return passed / max(checks, 1)

    # ── 降级方案 ─────────────────────────────────────────────────

    def _fallback_to_regex(
        self,
        raw_text: str,
        market: str,
        brand: str | None = None,
    ) -> dict[str, Any]:
        """降级到正则提取方案

        当 LLM 不可用或提取失败时，使用 RegexParamExtractor 作为后备。
        返回的 dict 包含 OUTPUT_SCHEMA 中能通过正则匹配的字段。

        Args:
            raw_text: 原始文本
            market:   目标市场代码
            brand:    品牌名称

        Returns:
            dict: 正则提取的参数（仅含匹配到的字段 + market + confidence）
        """
        regex_extractor = RegexParamExtractor()
        extracted = regex_extractor.extract_all(raw_text)

        # 字段名映射：正则 → OUTPUT_SCHEMA
        # power_w → cooling_w, heating_w（无法区分时都填入）
        if "power_w" in extracted and (
            "cooling_w" not in extracted and "heating_w" not in extracted
        ):
            pw = extracted.pop("power_w")
            extracted.setdefault("cooling_w", pw)
            extracted.setdefault("heating_w", pw)

        # price → factory_price
        if "price" in extracted and "factory_price" not in extracted:
            extracted["factory_price"] = str(extracted.pop("price"))

        # 填入元信息（用户传入的 brand 优先）
        if brand:
            extracted["brand"] = brand
        elif not extracted.get("brand"):
            extracted["brand"] = None
        extracted["market"] = market

        # 置信度
        extracted["confidence"] = self._calculate_confidence(extracted)

        return extracted
