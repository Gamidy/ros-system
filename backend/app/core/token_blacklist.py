"""Token 黑名单 — 登出撤销机制（内存版，生产环境替换为 Redis）"""

import time
from typing import Set, Tuple


# { token_hash: expiry_timestamp }
_blacklist: Set[Tuple[str, float]] = set()

# 每小时清理一次过期 token
_last_cleanup = time.time()


def _cleanup_expired():
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < 3600:
        return
    expired = {entry for entry in _blacklist if entry[1] < now}
    _blacklist.difference_update(expired)
    _last_cleanup = now


def blacklist_token(token: str, ttl: int = 28800) -> None:
    """将 token 加入黑名单

    Args:
        token: JWT token 原始字符串
        ttl: 黑名单有效期（秒），默认 8 小时 = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    """
    _cleanup_expired()
    # 只用 token 后 32 字符做 key（避免存完整 token）
    key = token[-32:] if len(token) >= 32 else token
    _blacklist.add((key, time.time() + ttl))


def is_blacklisted(token: str) -> bool:
    """检查 token 是否已被撤销"""
    _cleanup_expired()
    key = token[-32:] if len(token) >= 32 else token
    return any(entry[0] == key for entry in _blacklist)
