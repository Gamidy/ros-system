"""安全响应头中间件 — 从 main.py 拆分"""
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """添加安全响应头"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src \x27self\x27; "
            "script-src \x27self\x27; "
            "style-src \x27self\x27 \x27unsafe-inline\x27; "
            "img-src \x27self\x27 data:; "
            "font-src \x27self\x27; "
            "connect-src \x27self\x27; "
            "frame-ancestors \x27none\x27; "
            "base-uri \x27self\x27; "
            "form-action \x27self\x27"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
