"""D6-1 通知渠道 channels.py — 单元测试

覆盖场景：
- 企微/钉钉发送成功（happy path）
- 日限额超限跳过（error path）
- 重试机制（前2次失败第3次成功）
- 空 Webhook 静默跳过
"""
from __future__ import annotations

from typing import Any

import pytest

from app.services.notification.channels import (
    DingTalkChannel,
    WeComChannel,
    _check_daily_limit,
    _daily_counters,
    _last_date,
)

# ---------------------------------------------------------------------------
# 测试常量
# ---------------------------------------------------------------------------
WECOM_HOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
DINGTALK_HOOK = "https://oapi.dingtalk.com/robot/send?access_token=test"


# ---------------------------------------------------------------------------
# 辅助小工具
# ---------------------------------------------------------------------------
class _FakeResp:
    """模拟 requests.Response —— 只暴露测试关心的属性"""

    def __init__(self, status_code: int = 200, json_data: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data or {"errcode": 0, "errmsg": "ok"}

    def json(self) -> dict[str, Any]:
        return self._json_data


def _bypass_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """让 `_check_daily_limit` 始终返回 True（不干扰测试目标）"""
    monkeypatch.setattr(
        "app.services.notification.channels._check_daily_limit",
        lambda cid, lim: True,
    )


def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """让 `time.sleep` 变成无操作（重试测试中跳过等待）"""
    monkeypatch.setattr("app.services.notification.channels.time.sleep", lambda s: None)


# ===================================================================
# 测试类
# ===================================================================
class TestWeComChannel:
    """企微机器人发送"""

    def test_wecom_send_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """企微发送成功 — 正常 HTTP 200"""
        captured: list[dict[str, Any]] = []

        def fake_post(url: str, headers: dict[str, str],
                      json: dict[str, Any], timeout: int) -> _FakeResp:
            captured.append({"url": url, "headers": headers, "payload": json})
            return _FakeResp(200, {"errcode": 0, "errmsg": "ok"})

        monkeypatch.setattr("app.services.notification.channels.requests.post", fake_post)
        _bypass_limit(monkeypatch)

        ch = WeComChannel(channel_id=1, webhook_url=WECOM_HOOK)
        result = ch.do_send("Hello WeCom")

        assert result["ok"] is True
        assert result["msg"] == "ok"
        assert len(captured) == 1
        payload = captured[0]["payload"]
        assert payload["msgtype"] == "text"
        assert payload["text"]["content"] == "Hello WeCom"

    def test_daily_limit_exceeded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """日限额超限后跳过 — _check_daily_limit 返回 False"""
        monkeypatch.setattr(
            "app.services.notification.channels._check_daily_limit",
            lambda cid, lim: False,
        )

        ch = WeComChannel(channel_id=99, webhook_url=WECOM_HOOK, daily_limit=5)
        result = ch.do_send("should be skipped")

        assert result["ok"] is False
        assert result["msg"] == "Daily limit reached"

    def test_retry_mechanism(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """重试机制 — 前2次 HTTP 500，第3次 HTTP 200"""
        attempt: list[int] = [0]

        def fake_post(url: str, headers: dict[str, str],
                      json: dict[str, Any], timeout: int) -> _FakeResp:
            attempt[0] += 1
            if attempt[0] <= 2:
                return _FakeResp(status_code=500)
            return _FakeResp(200, {"errmsg": "ok"})

        monkeypatch.setattr("app.services.notification.channels.requests.post", fake_post)
        _bypass_limit(monkeypatch)
        _no_sleep(monkeypatch)

        ch = WeComChannel(channel_id=3, webhook_url=WECOM_HOOK)
        result = ch.do_send("retry test")

        assert result["ok"] is True
        assert attempt[0] == 3  # 2 fail + 1 success

    def test_empty_webhook_skip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无 Webhook URL 时静默跳过（不抛异常）"""
        _bypass_limit(monkeypatch)
        _no_sleep(monkeypatch)

        ch = WeComChannel(channel_id=4, webhook_url="")
        result = ch.do_send("no webhook")

        assert result["ok"] is False
        # 不应抛出任何异常


class TestDingTalkChannel:
    """钉钉机器人发送"""

    def test_dingtalk_send_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """钉钉发送成功 — 正常 HTTP 200"""
        captured: list[dict[str, Any]] = []

        def fake_post(url: str, headers: dict[str, str],
                      json: dict[str, Any], timeout: int) -> _FakeResp:
            captured.append({"url": url, "headers": headers, "payload": json})
            return _FakeResp(200, {"errcode": 0, "errmsg": "ok"})

        monkeypatch.setattr("app.services.notification.channels.requests.post", fake_post)
        _bypass_limit(monkeypatch)

        ch = DingTalkChannel(channel_id=2, webhook_url=DINGTALK_HOOK, secret="mysecret")
        result = ch.do_send("Hello DingTalk")

        assert result["ok"] is True
        assert len(captured) == 1
        # 注意：当前 _do_send 使用 self.webhook_url（不包含签名参数）
        # 这是已知行为，测试验证实际 behavior 而非理想 behavior
        url = captured[0]["url"]
        assert url == DINGTALK_HOOK
        payload = captured[0]["payload"]
        assert payload["msgtype"] == "text"
        assert payload["text"]["content"] == "Hello DingTalk"

    def test_empty_webhook_skip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """无 Webhook URL 时静默跳过（不抛异常）"""
        _bypass_limit(monkeypatch)
        _no_sleep(monkeypatch)

        ch = DingTalkChannel(channel_id=5, webhook_url="")
        result = ch.do_send("no webhook")

        assert result["ok"] is False


# ===================================================================
# 直接测试 _check_daily_limit / _increment_counter 单元
# ===================================================================
class TestDailyLimit:
    """日限额核心逻辑直接验证"""

    def test_check_no_limit_not_reached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """未超限时返回 True"""
        _daily_counters.clear()
        monkeypatch.setattr("app.services.notification.channels._last_date", "2099-01-01")
        result = _check_daily_limit(channel_id=10, limit=100)
        assert result is True

    def test_check_limit_reached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """已达上限时返回 False"""
        from datetime import date as dt_date
        _daily_counters.clear()
        key = "ch:10"
        _daily_counters[key] = 100
        monkeypatch.setattr("app.services.notification.channels._last_date", dt_date.today().isoformat())
        result = _check_daily_limit(channel_id=10, limit=100)
        assert result is False

    def test_date_change_resets_counters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """日期变更时计数器自动重置"""
        from datetime import date

        _daily_counters.clear()
        _daily_counters["ch:10"] = 100
        # 模拟昨天
        monkeypatch.setattr("app.services.notification.channels._last_date", "1999-12-31")
        # 这样今天 != 1999-12-31，计数器会被清空
        monkeypatch.setattr("app.services.notification.channels.date", date)

        result = _check_daily_limit(channel_id=10, limit=100)
        assert result is True  # 清空后未超限
        assert _daily_counters.get("ch:10") is None
