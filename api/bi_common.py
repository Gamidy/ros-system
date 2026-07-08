"""BI分析 — 共享工具函数"""
import json
import logging
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)
CACHE_TTL = 600

def _redis_client() -> Optional['redis.Redis']:
    """尝试获取 Redis 连接，失败返回 None 避免影响主流程"""
    global _redis_pool
    try:
        import redis as _redis
        if _redis_pool is None:
            _redis_pool = _redis.ConnectionPool(
                host="127.0.0.1", port=6379, socket_connect_timeout=1, decode_responses=True
            )
        return _redis.Redis(connection_pool=_redis_pool)
    except Exception:
        return None



def _cache_get(key: str) -> Optional[str]:
    """从 Redis 读取缓存，Redis 不可用时返回 None"""
    try:
        r = _redis_client()
        if r is None:
            return None
        val: Optional[str] = r.get(key)
        return val
    except Exception:
        return None



def _cache_set(key: str, value: str, ttl: int = 600) -> None:
    """写入 Redis 缓存，失败静默忽略"""
    try:
        r = _redis_client()
        if r is None:
            return
        r.setex(key, ttl, value)
    except Exception:
        pass


CACHE_TTL = 600  # 10分钟


# ═══════════════════════════════════════════
# 策划维度统计
# ═══════════════════════════════════════════

@router.get("/planning")

