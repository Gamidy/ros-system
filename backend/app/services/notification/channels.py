"""消息推送通道 — 抽象基类 + 企微/钉钉实现"""
import abc
import hashlib
import hmac
import base64
import json
import time
import logging
from typing import Optional
from datetime import date, datetime

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 日限额管理器（进程内内存计数 — 生产环境建议替换为 Redis）
# ---------------------------------------------------------------------------
_daily_counters: dict[str, int] = {}
_last_date: Optional[str] = None


def _check_daily_limit(channel_id: int, limit: int) -> bool:
    """检查是否超限；返回 False 表示已达上限"""
    global _last_date
    today = date.today().isoformat()
    if _last_date != today:
        _daily_counters.clear()
        _last_date = today
    key = f"ch:{channel_id}"
    if _daily_counters.get(key, 0) >= limit:
        logger.warning("Channel %s daily limit %d reached", channel_id, limit)
        return False
    return True


def _increment_counter(channel_id: int):
    key = f"ch:{channel_id}"
    _daily_counters[key] = _daily_counters.get(key, 0) + 1


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------
class MessageChannel(abc.ABC):
    """消息通道抽象基类"""

    def __init__(self, channel_id: int, webhook_url: str, secret: str = "",
                 daily_limit: int = 1000):
        self.channel_id = channel_id
        self.webhook_url = webhook_url.rstrip("/")
        self.secret = secret
        self.daily_limit = daily_limit

    @abc.abstractmethod
    def send(self, content: str) -> dict:
        """发送消息 → {"ok": bool, "msg": str}"""
        ...

    def _do_send(self, content: str, headers: dict,
                 payload: dict) -> dict:
        """执行 HTTP POST，含指数退避重试 (3 次)"""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    self.webhook_url,
                    headers=headers,
                    json=payload,
                    timeout=10,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    return {"ok": True, "msg": body.get("errmsg", "ok")}
                # 非 200 — 重试
                logger.warning(
                    "Channel %s attempt %d/%d HTTP %s",
                    self.channel_id, attempt, max_retries, resp.status_code,
                )
            except requests.RequestException as e:
                logger.warning(
                    "Channel %s attempt %d/%d error: %s",
                    self.channel_id, attempt, max_retries, e,
                )
            if attempt < max_retries:
                sleep_sec = 2 ** attempt  # 2, 4, 8 秒
                time.sleep(sleep_sec)
        return {"ok": False, "msg": "All retries exhausted"}

    def do_send(self, content: str) -> dict:
        """公开入口：日限额检查 → 发送 → 计数"""
        if not _check_daily_limit(self.channel_id, self.daily_limit):
            return {"ok": False, "msg": "Daily limit reached"}
        result = self.send(content)
        if result.get("ok"):
            _increment_counter(self.channel_id)
        return result


# ---------------------------------------------------------------------------
# 企微群机器人
# ---------------------------------------------------------------------------
class WeComChannel(MessageChannel):
    """企业微信群机器人 Webhook"""

    def send(self, content: str) -> dict:
        headers = {"Content-Type": "application/json"}
        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }
        return self._do_send(content, headers, payload)


# ---------------------------------------------------------------------------
# 钉钉自定义机器人
# ---------------------------------------------------------------------------
class DingTalkChannel(MessageChannel):
    """钉钉自定义机器人 Webhook（支持签名校验）"""

    def send(self, content: str) -> dict:
        timestamp = str(round(time.time() * 1000))
        sign = self._sign(timestamp)
        headers = {"Content-Type": "application/json"}
        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }
        url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
        return self._do_send(content, headers, payload)

    def _sign(self, timestamp: str) -> str:
        sign_str = f"{timestamp}\n{self.secret}"
        sign_bytes = hmac.new(
            self.secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(sign_bytes).decode("utf-8")
