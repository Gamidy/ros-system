"""Redis缓存管理 — 统一的缓存装饰器和工具函数（原则22: 缓存策略）"""
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import redis
    _redis_client: Optional[redis.Redis] = None

    def get_redis() -> Optional[redis.Redis]:
        global _redis_client
        if _redis_client is None:
            try:
                _redis_client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
                _redis_client.ping()
            except Exception as e:
                logger.warning("Redis 不可用，缓存降级: %s", e)
                _redis_client = None
        return _redis_client
except ImportError:
    def get_redis() -> None:
        return None

def cache_result(ttl: int = 300):
    """缓存函数返回结果（原则22: 缓存策略）"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = get_redis()
            if r is None:
                return func(*args, **kwargs)
            # Simple key based on function name and args
            key = f"cache:{func.__name__}:{hash(tuple(args))}:{hash(tuple(sorted(kwargs.items())))}"
            try:
                cached = r.get(key)
                if cached is not None:
                    return json.loads(cached)
            except Exception:
                pass
            result = func(*args, **kwargs)
            try:
                r.setex(key, ttl, json.dumps(result, default=str))
            except Exception:
                pass
            return result
        return wrapper
    return decorator
