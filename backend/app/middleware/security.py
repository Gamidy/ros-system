"""Phase 2.2 — 安全中间件: XSS防护 + CSRF + Security Headers

参考 ROS 系统设计，提供纵深防护:
1. XSSProtectionMiddleware — 请求体 HTML 转义
2. SecurityHeadersMiddleware — 安全响应头
3. CSRF 工具函数 — 双提交 Cookie 模式

由于 PLM 使用 JWT Bearer token（非 cookie 认证），天然免疫传统 CSRF，
但提供 CSRF 机制作为纵深防护。
"""

import html
import secrets
import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# XSS 防护
# ═══════════════════════════════════════════════════════

def sanitize_html(value: str) -> str:
    """转义 HTML 特殊字符，防御存储型 XSS

    >>> sanitize_html('<img src=x onerror=alert(1)>')
    '&lt;img src=x onerror=alert(1)&gt;'
    """
    return html.escape(value, quote=True)


def sanitize_dict(d: dict) -> dict:
    """递归清洗 dict 中所有字符串值"""
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = sanitize_html(v)
        elif isinstance(v, dict):
            sanitize_dict(v)
        elif isinstance(v, list):
            d[k] = [
                sanitize_html(item) if isinstance(item, str) else item
                for item in v
            ]
    return d


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """XSS 防护中间件 — 添加 XSS 防护响应头

    注意: 由于 ASGI 请求体只能读取一次，body 清洗逻辑不在此处执行。
    真正的内容清洗应在 API 层调用 sanitize_html/sanitize_dict。
    此中间件仅添加响应头提示浏览器启用 XSS 过滤器。
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if isinstance(response, Response):
            response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


# ═══════════════════════════════════════════════════════
# Security Headers
# ═══════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """添加安全响应头"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        return response


# ═══════════════════════════════════════════════════════
# CSRF 纵深防护（双提交 Cookie）
# ═══════════════════════════════════════════════════════

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """生成随机 CSRF token"""
    return secrets.token_hex(32)


def set_csrf_cookie(response: Response) -> str:
    """在响应中设置 CSRF cookie"""
    token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,         # 前端 JS 需要读取
        samesite="strict",
        secure=True,
        max_age=86400,          # 24 小时
    )
    return token


async def csrf_middleware(request: Request, call_next):
    """CSRF 检查 — state-changing 请求校验 X-CSRF-Token"""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if cookie_token is None:
        return await call_next(request)  # 无 cookie，跳过（向后兼容）

    if not header_token or not secrets.compare_digest(cookie_token, header_token):
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF token 校验失败"},
        )

    return await call_next(request)
