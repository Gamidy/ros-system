"""AI 服务统一接口 — ai_chat() 入口 + 供应商工厂

用法:
    from app.services.ai import ai_chat

    result = await ai_chat(
        provider="deepseek",
        model="deepseek-chat",
        messages=[{"role": "user", "content": "你好"}],
        api_key="sk-xxx",
    )
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.ai.base import (
    AIProvider,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    OpenAICompatibleProvider,
    get_provider,
    register_provider,
)
from app.models.ai_call_log import AICallLog

logger = logging.getLogger(__name__)

__all__ = [
    "ai_chat",
    "AIProvider",
    "OpenAICompatibleProvider",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "get_provider",
    "register_provider",
]


async def ai_chat(
    *,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    api_key: str,
    api_base: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    request_id: Optional[str] = None,
    log_to_db: bool = False,
    db_session=None,
    **extra_kwargs,
) -> ChatResponse:
    """统一 AI 聊天入口

    Args:
        provider:   供应商名称 (openai / deepseek / qwen / moonshot / zhipu)
        model:      模型名称 (gpt-4o / deepseek-chat / qwen-plus 等)
        messages:   消息列表，格式 [{"role": "user", "content": "..."}]
        api_key:    API 密钥（明文）
        api_base:   可选的 API Base URL，不填则使用供应商默认
        temperature: 温度参数
        max_tokens:  最大输出 token 数
        request_id:  请求 ID（自动生成 UUID 若未传）
        log_to_db:   是否写入 ai_call_logs 表
        db_session:  数据库 Session（log_to_db=True 时必传）
        **extra_kwargs: 传递给供应商的额外参数

    Returns:
        ChatResponse
    """
    req_id = request_id or str(uuid.uuid4())

    provider_instance = get_provider(
        name=provider,
        api_key=api_key,
        api_base=api_base,
    )

    chat_req = ChatRequest(
        model=model,
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in messages],
        temperature=temperature,
        max_tokens=max_tokens,
        extra=extra_kwargs,
    )

    result = await provider_instance.chat(chat_req)

    # 可选: 写入调用日志
    if log_to_db and db_session is not None:
        try:
            log_entry = AICallLog(
                request_id=req_id,
                provider=provider,
                model=model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost=result.cost,
                response_time_ms=result.response_time_ms,
                success=result.success,
                error=result.error[:500] if result.error else None,
            )
            db_session.add(log_entry)
            db_session.commit()
        except Exception as e:
            logger.warning("Failed to persist ai_call_log: %s", e)
            db_session.rollback()

    return result
