"""
AI策划草案生成器

流程:
1. 调用 d4t2 aggregate_market_context() 聚合市场数据
2. 构建 system prompt（含策划模板结构，支持从 prompt_templates 表动态加载）
3. 调用 d4t1 ai_chat() 请求 LLM
4. 解析 JSON 输出为结构化策划草案
"""
import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.ai import ai_chat
from app.services.ai.market_aggregator import aggregate_market_context
from app.models.prompt_template import PromptTemplate

logger = logging.getLogger(__name__)

# ── 默认策划模板结构（作为 fallback system prompt 内容） ──

DEFAULT_PLAN_TEMPLATE = """你是一位资深空调产品策划专家。基于以下聚合的市场数据，生成一份结构化的新产品策划草案。

## 策划模板结构

请严格按照以下 JSON 结构输出策划草案（只输出 JSON，不包含任何额外说明）：

{
  "plan_name": "策划名称（建议的品牌+系列+容量）",
  "product_type": "产品类型（如 split_wall/floor_standing/cassette/duct）",
  "series": "产品系列名",
  "target_market_detail": "目标市场详细描述",
  "capacity_range": "容量范围描述（如 9000-12000 BTU/h）",
  "core_performance": {
    "cooling_capacity_btu": "制冷能力（BTU/h）",
    "cooling_capacity_w": "制冷能力（W）",
    "heating_capacity_w": "制热能力（W）（如有）",
    "cooling_eer": "目标能效比 EER",
    "heating_cop": "目标制热 COP",
    "energy_rating": "目标能效等级",
    "cspf": "CSPF 值（如有）",
    "voltage_freq": "电压频率（如 220V/50Hz）",
    "refrigerant": "制冷剂类型（如 R32/R410A）"
  },
  "market_positioning": {
    "target_market_segment": "目标细分市场（低端/中端/高端）",
    "key_differentiators": ["差异化卖点1", "差异化卖点2"],
    "suggested_price_range": "建议价格区间（元）",
    "target_markets": ["目标国家/地区列表"]
  },
  "technical_specs": {
    "noise_indoor_db_max": "室内机最大噪音 dB(A)",
    "noise_outdoor_db_max": "室外机最大噪音 dB(A)",
    "airflow_m3h": "循环风量 m³/h",
    "dimensions_indoor": "室内机尺寸（mm）",
    "dimensions_outdoor": "室外机尺寸（mm）",
    "weight_indoor_kg": "室内机重量（kg）",
    "weight_outdoor_kg": "室外机重量（kg）",
    "pipe_connections": "管路连接规格"
  },
  "cost_targets": {
    "target_factory_cost": "目标工厂成本（元）",
    "key_cost_drivers": ["主要成本驱动因素"],
    "cost_reduction_opportunities": ["降本机会点"]
  },
  "compliance_requirements": {
    "required_standards": ["所需符合的标准代码"],
    "required_certifications": ["所需认证类型"],
    "required_tests": ["所需测试项目"]
  },
  "competitor_benchmarks": [
    {
      "brand": "竞品品牌",
      "model": "竞品型号",
      "key_strengths": ["优势"],
      "key_weaknesses": ["劣势"]
    }
  ],
  "risk_assessment": {
    "technical_risks": ["技术风险"],
    "market_risks": ["市场风险"],
    "cost_risks": ["成本风险"],
    "mitigation_strategies": ["应对策略"]
  },
  "development_timeline": {
    "suggested_duration_months": "建议开发周期（月）",
    "key_milestones": ["关键里程碑节点"]
  }
}

## 分析要求

1. 基于实际聚合的市场数据（竞品、能效标准、历史策划、成本基准）进行决策
2. 能效等级和性能目标必须满足目标市场的最低标准要求
3. 价格定位应考虑竞品价格区间和成本基准数据
4. 技术规格需结合历史策划和竞品水平设定合理目标
5. 风险分析要具体到该产品和市场的实际情况
6. 差异化卖点应基于竞品分析的空白点或优势领域

## 输出规则

- 只输出合法的 JSON 对象，不要包含 markdown 代码块标记或任何额外文字
- 所有字段使用驼峰命名法（camelCase）
- 如果某个字段没有数据，使用 null 而非空字符串
- 数值字段使用数字类型，不要加引号
"""

# ── 默认 system prompt wrapper（围绕模板） ──

DEFAULT_SYSTEM_PROMPT = """你是 ROS 系统的 AI 策划助手，专精于空调（AC）产品策划。请根据以下聚合的市场上下文信息和策划模板结构，生成一份结构化的产品策划草案。

市场上下文数据：
{market_context_json}

策划模板结构（请严格按此 JSON schema 输出）：
{template_structure}

注意：只输出合法的 JSON 对象，不要包含 markdown 代码块标记或任何额外文字。"""


def _load_template(db: Session, template_name: str) -> Optional[str]:
    """从 prompt_templates 表加载启用的模板内容"""
    row = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.name == template_name, PromptTemplate.enabled == True)
        .order_by(PromptTemplate.version.desc())
        .first()
    )
    if row:
        logger.info("Loaded prompt template '%s' (v%d)", row.name, row.version)
        return row.content
    return None


def _build_system_prompt(
    market_context: dict[str, Any],
    product_type: str,
    extra_context: Optional[str] = None,
    db: Optional[Session] = None,
) -> str:
    """构建 system prompt

    优先级:
    1. 从 prompt_templates 表加载 'plan_generator_system' 模板
    2. 从 prompt_templates 表加载 'plan_template_structure' 模板
    3. 使用内置默认模板
    """
    market_json = json.dumps(market_context, ensure_ascii=False, indent=2, default=str)
    extra_json = json.dumps(extra_context, ensure_ascii=False, indent=2, default=str) if extra_context else "{}"

    # 尝试从数据库加载 system prompt 模板
    system_prompt_template = None
    template_structure = None

    if db is not None:
        system_prompt_template = _load_template(db, "plan_generator_system")
        template_structure = _load_template(db, "plan_template_structure")

    # fallback 到内置默认
    if not system_prompt_template:
        system_prompt_template = DEFAULT_SYSTEM_PROMPT
    if not template_structure:
        template_structure = DEFAULT_PLAN_TEMPLATE

    # 填充变量
    prompt = system_prompt_template.format(
        market_context_json=market_json,
        template_structure=template_structure,
        product_type=product_type,
        extra_context=extra_json,
    )

    return prompt


def _parse_plan_draft(raw_text: str) -> dict[str, Any]:
    """解析 LLM 返回的文本为 JSON 策划草案

    尝试多种解析策略：
    1. 直接 json.loads
    2. 提取 ```json ... ``` 代码块
    3. 提取 ``` ... ``` 代码块
    """
    text = raw_text.strip()

    # 策略1: 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 策略2: 提取 ```json ... ``` 代码块
    import re
    json_match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 策略3: 提取 ``` ... ``` 代码块
    code_match = re.search(r"```\s*\n(.*?)\n```", text, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass

    # 策略4: 尝试找到第一个 { 到最后一个 }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    logger.error("Failed to parse AI response as JSON: %.200s...", raw_text)
    raise ValueError("AI 返回的内容无法解析为有效的 JSON 格式")


async def generate_plan_draft(
    market_id: int,
    product_type: str,
    extra_context: Optional[str] = None,
    *,
    db: Optional[Session] = None,
    provider: str = "deepseek",
    model: str = "deepseek-chat",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> dict[str, Any]:
    """生成策划草案

    Parameters
    ----------
    market_id : int
        目标市场 ID
    product_type : str
        产品类型（如 split_wall / floor_standing / cassette / duct）
    extra_context : str, optional
        额外上下文信息（JSON 字符串），供 AI 参考
    db : Session, optional
        SQLAlchemy 数据库会话。未提供时自动创建新会话。
    provider : str
        AI 供应商名称（默认 deepseek）
    model : str
        模型名称（默认 deepseek-chat）
    api_key : str, optional
        API 密钥。未提供时尝试从 settings 读取。
    api_base : str, optional
        自定义 API Base URL

    Returns
    -------
    dict
        结构化策划草案，包含 fields: plan_name, product_type, core_performance,
        market_positioning, technical_specs, cost_targets, compliance_requirements,
        competitor_benchmarks, risk_assessment, development_timeline
    """
    # ── 1. 获取或创建 DB 会话 ──
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        # ── 2. 聚合市场数据 ──
        logger.info("Aggregating market context for market_id=%d", market_id)
        market_context = aggregate_market_context(market_id, db=db)
        if "error" in market_context:
            raise ValueError(market_context["error"])

        # ── 3. 构建 system prompt ──
        system_prompt = _build_system_prompt(
            market_context=market_context,
            product_type=product_type,
            extra_context=extra_context,
            db=db,
        )

        # ── 4. 调用 AI ──
        logger.info("Calling AI provider=%s model=%s for plan generation", provider, model)

        # 尝试从 app.core.config 获取默认 API key
        if not api_key:
            try:
                from app.core.config import settings
                api_key = getattr(settings, "AI_API_KEY", None) or getattr(settings, "DEEPSEEK_API_KEY", None)
            except Exception as e:
                logger.warning(f"获取 settings AI_API_KEY 失败: {e}")
                pass

        if not api_key:
            raise ValueError(
                "缺少 API key。请通过参数 api_key 传入，或在 settings 中配置 AI_API_KEY / DEEPSEEK_API_KEY。"
            )

        chat_result = await ai_chat(
            provider=provider,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"请为目标市场（ID: {market_id}）生成一份 {product_type} 类型产品策划草案。"
                        f"额外上下文：{extra_context or '无'}"
                    ),
                },
            ],
            api_key=api_key,
            api_base=api_base,
            temperature=0.7,
            max_tokens=8192,
        )

        if not chat_result.success:
            logger.error("AI chat failed: %s", chat_result.error)
            raise RuntimeError(f"AI 调用失败: {chat_result.error}")

        # ── 5. 解析 JSON 输出 ──
        plan_draft = _parse_plan_draft(chat_result.text)

        # 补充元信息
        plan_draft["_meta"] = {
            "market_id": market_id,
            "product_type": product_type,
            "model": chat_result.model,
            "provider": chat_result.provider,
            "prompt_tokens": chat_result.prompt_tokens,
            "completion_tokens": chat_result.completion_tokens,
            "cost": chat_result.cost,
            "response_time_ms": chat_result.response_time_ms,
        }

        logger.info(
            "Plan draft generated successfully: %s tokens=%d+%d cost=%.6f",
            plan_draft.get("plan_name", "N/A"),
            chat_result.prompt_tokens,
            chat_result.completion_tokens,
            chat_result.cost,
        )

        return plan_draft

    finally:
        if own_session:
            db.close()
