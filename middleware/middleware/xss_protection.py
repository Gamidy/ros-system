"""XSS 响应层防护中间件 — 对所有 JSON 响应中的字符串字段做 HTML 转义

作为纵深防御层，即使输入未做 sanitize，输出时也确保安全。
覆盖所有 API 端点，无需逐个修改。
"""
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from starlette.responses import Response
from app.core.security import sanitize_html

logger = logging.getLogger(__name__)


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """响应层 XSS 防护中间件

    拦截所有 JSON 响应，递归转义字符串字段中的 HTML 特殊字符。
    不处理 StreamingResponse / FileResponse（无 body 属性）。
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 只处理 JSON 响应
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type and "text/json" not in content_type:
            return response

        try:
            body = getattr(response, "body", None)
            if not body:
                return response

            data = json.loads(body)
            sanitized = _sanitize_json(data)
            return Response(
                content=json.dumps(sanitized, ensure_ascii=False, default=str),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )
        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            logger.warning("XSS 防护中间件处理失败: %s", exc)
            return response


def _sanitize_json(obj):
    """递归转义 JSON 树中的字符串值"""
    if isinstance(obj, str):
        return sanitize_html(obj)
    elif isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    return obj
