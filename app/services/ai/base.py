"""AI 供应商抽象层 — 定义统一接口及 OpenAI 兼容协议实现"""
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)


# ─── 数据对象 ─────────────────────────────────────────────────────────


@dataclass
class ChatMessage:
    """对话消息"""
    role: str  # system / user / assistant
    content: str


@dataclass
class ChatRequest:
    """统一的聊天请求参数"""
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """统一的聊天响应"""
    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    response_time_ms: int = 0
    success: bool = True
    error: Optional[str] = None


# ─── 成本计价表（每 1K token 的美元价格） ─────────────────────────────

_DEFAULT_COST_TABLE: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o":              {"input": 0.0025, "output": 0.010},
    "gpt-4o-mini":         {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo":         {"input": 0.01, "output": 0.03},
    # DeepSeek
    "deepseek-chat":       {"input": 0.0005, "output": 0.002},
    "deepseek-reasoner":   {"input": 0.002, "output": 0.008},
    # 通义千问
    "qwen-plus":           {"input": 0.0008, "output": 0.002},
    "qwen-turbo":          {"input": 0.0003, "output": 0.0006},
    "qwen-max":            {"input": 0.002, "output": 0.006},
    # 月之暗面 Moonshot
    "moonshot-v1-8k":      {"input": 0.012, "output": 0.012},
    "moonshot-v1-32k":     {"input": 0.024, "output": 0.024},
    # 智谱 GLM
    "glm-4-plus":          {"input": 0.005, "output": 0.005},
    "glm-4-air":           {"input": 0.001, "output": 0.001},
    # Cloude (Anthropic)
    "claude-3-5-sonnet":   {"input": 0.003, "output": 0.015},
    "claude-3-opus":       {"input": 0.015, "output": 0.075},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """根据内置计价表估算调用费用（美元）"""
    prices = _DEFAULT_COST_TABLE.get(model)
    if prices is None:
        return 0.0
    input_cost = (prompt_tokens / 1000) * prices["input"]
    output_cost = (completion_tokens / 1000) * prices["output"]
    return round(input_cost + output_cost, 6)


# ─── 抽象基类 ─────────────────────────────────────────────────────────


class AIProvider(ABC):
    """AI 供应商抽象基类 — 所有供应商实现必须继承此类"""

    def __init__(self, *, api_key: str, api_base: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.api_base = (api_base or self._default_api_base()).rstrip("/")
        self._client = httpx.AsyncClient(timeout=60.0)

    @abstractmethod
    def _default_api_base(self) -> str:
        """返回该供应商的默认 API Base URL"""
        ...

    @abstractmethod
    def _chat_endpoint(self) -> str:
        """返回聊天补全 API 的完整 URL"""
        ...

    @abstractmethod
    def _build_headers(self) -> dict[str, str]:
        """构建请求头"""
        ...

    @abstractmethod
    def _build_request_body(self, req: ChatRequest) -> dict:
        """构建请求体"""
        ...

    @abstractmethod
    def _parse_response(self, raw: dict, start_time: float) -> ChatResponse:
        """解析供应商原始响应为统一 ChatResponse"""
        ...

    async def chat(self, req: ChatRequest) -> ChatResponse:
        """统一的异步聊天入口"""
        start = time.monotonic()
        try:
            resp = await self._client.post(
                url=self._chat_endpoint(),
                headers=self._build_headers(),
                json=self._build_request_body(req),
            )
            resp.raise_for_status()
            raw = resp.json()
            result = self._parse_response(raw, start)
            # 补充未由解析器提供的字段
            result.provider = self.__class__.__name__.replace("Provider", "").lower()
            result.response_time_ms = int((time.monotonic() - start) * 1000)
            if result.total_tokens == 0:
                result.total_tokens = result.prompt_tokens + result.completion_tokens
            if result.cost == 0.0 and result.total_tokens > 0:
                result.cost = _estimate_cost(req.model, result.prompt_tokens, result.completion_tokens)
            return result
        except httpx.HTTPStatusError as e:
            elapsed = int((time.monotonic() - start) * 1000)
            body = e.response.text[:500] if e.response else str(e)
            return ChatResponse(
                text="",
                model=req.model,
                provider=self.__class__.__name__.replace("Provider", "").lower(),
                response_time_ms=elapsed,
                success=False,
                error=f"HTTP {e.response.status_code}: {body}" if e.response else str(e),
            )
        except Exception as e:
            logger.exception("unexpected error")
            elapsed = int((time.monotonic() - start) * 1000)
            logger.exception("AIProvider.chat error")
            return ChatResponse(
                text="",
                model=req.model,
                provider=self.__class__.__name__.replace("Provider", "").lower(),
                response_time_ms=elapsed,
                success=False,
                error=str(e),
            )

    async def close(self) -> None:
        await self._client.aclose()


# ─── OpenAI 兼容供应商 ───────────────────────────────────────────────


class OpenAICompatibleProvider(AIProvider):
    """兼容 OpenAI API 协议的供应商实现

    适用于: OpenAI / DeepSeek / 通义千问(Qwen) / Moonshot / GLM 等
    标准 ChatCompletion API 路径: POST /v1/chat/completions
    """

    def _default_api_base(self) -> str:
        return "https://api.openai.com"

    def _chat_endpoint(self) -> str:
        return f"{self.api_base}/v1/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_request_body(self, req: ChatRequest) -> dict:
        body = {
            "model": req.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": req.stream,
        }
        body.update(req.extra)
        return body

    def _parse_response(self, raw: dict, start_time: float) -> ChatResponse:
        usage = raw.get("usage", {})
        choice = raw.get("choices", [{}])[0]
        message = choice.get("message", {})
        text = message.get("content", "")

        return ChatResponse(
            text=text,
            model=raw.get("model", ""),
            provider="",  # 由上层填充
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            response_time_ms=int((time.monotonic() - start_time) * 1000),
        )


# ─── 供应商工厂 ───────────────────────────────────────────────────────


_PROVIDER_MAP: dict[str, type[AIProvider]] = {
    "openai": OpenAICompatibleProvider,
    "deepseek": OpenAICompatibleProvider,
    "qwen": OpenAICompatibleProvider,
    "moonshot": OpenAICompatibleProvider,
    "zhipu": OpenAICompatibleProvider,
    "siliconflow": OpenAICompatibleProvider,
    "siliconflow": OpenAICompatibleProvider,
}


def register_provider(name: str, cls: type[AIProvider]) -> None:
    """注册自定义供应商实现"""
    _PROVIDER_MAP[name] = cls


def get_provider(name: str, **kwargs) -> AIProvider:
    """根据名称获取供应商实例"""
    cls = _PROVIDER_MAP.get(name)
    if cls is None:
        raise ValueError(f"Unknown AI provider: {name}. Available: {list(_PROVIDER_MAP.keys())}")
    return cls(**kwargs)
