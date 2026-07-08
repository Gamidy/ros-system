"""滑动窗口限流中间件 — 按 IP + 用户维度限制请求频率"""
import time
from collections import defaultdict
from typing import DefaultDict
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from app.core.config import settings

# 豁免路径（不参与限流）
EXEMPT_PATHS = {"/health", "/api/auth/login"}

# 限流配置 — 有效限流
IP_LIMIT = 100        # 100 req/min per IP
USER_LIMIT = 200      # 200 req/min per user
WINDOW_SECONDS = 60   # 滑动窗口 60 秒


class RateLimitMiddleware(BaseHTTPMiddleware):
    """滑动窗口限流中间件

    - 按 IP 维度: 100 req/min
    - 按用户维度: 200 req/min（从 JWT token 提取 user_id）
    - 豁免 /health 和 /auth/login
    """

    def __init__(self, app):
        super().__init__(app)
        # IP → 请求时间戳列表
        self._ip_requests: DefaultDict[str, list[float]] = defaultdict(list)
        # user_id → 请求时间戳列表
        self._user_requests: DefaultDict[str, list[float]] = defaultdict(list)

    def _clean_window(self, bucket: list[float], now: float) -> list[float]:
        """清理滑动窗口外的旧时间戳，返回窗口内剩余"""
        cutoff = now - WINDOW_SECONDS
        # 找到第一个 >= cutoff 的索引并切片
        for i, ts in enumerate(bucket):
            if ts >= cutoff:
                return bucket[i:]
        return []

    def _check_and_record(self, bucket_key: str, store: DefaultDict[str, list[float]], limit: int, label: str) -> bool:
        """检查并记录请求，返回 True 表示放行，False 表示触发限流"""
        now = time.time()
        bucket = store[bucket_key]
        bucket.append(now)
        # 清理旧记录
        store[bucket_key] = self._clean_window(bucket, now)
        return len(store[bucket_key]) <= limit

    async def dispatch(self, request: Request, call_next):
        # 豁免路径直接放行
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # 获取客户端 IP
        ip = request.client.host if request.client else "unknown"

        # 提取用户 ID（从 JWT token）
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
                )
                user_id = payload.get("sub")
            except JWTError as exc:
                pass  # token 无效时仅按 IP 限流

        # IP 维度限流
        if not self._check_and_record(ip, self._ip_requests, IP_LIMIT, "IP"):
            return JSONResponse(
                status_code=429,
                content={"detail": f"请求过于频繁，请稍后再试 (IP 限制 {IP_LIMIT}次/分钟)"},
            )

        # 用户维度限流（仅限已认证用户）
        if user_id:
            if not self._check_and_record(str(user_id), self._user_requests, USER_LIMIT, "User"):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后再试 (用户限制 200次/分钟)"},
                )

        return await call_next(request)
