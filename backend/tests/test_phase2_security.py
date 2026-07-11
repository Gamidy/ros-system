"""Phase 2.2 — 状态机 + 安全中间件 测试"""

import pytest

from app.services.state_machine import (
    assert_transition, get_valid_transitions,
    is_terminal, TransitionError,
)
from app.middleware.security import sanitize_html, sanitize_dict


class TestStateMachine:
    """统一状态机测试"""

    def test_project_transitions(self):
        assert "running" in get_valid_transitions("Project", "planning")
        assert "completed" in get_valid_transitions("Project", "running")
        assert get_valid_transitions("Project", "completed") == []

    def test_ecr_transitions(self):
        assert "submitted" in get_valid_transitions("ECR", "draft")
        assert "approved" in get_valid_transitions("ECR", "reviewing")
        assert "rejected" in get_valid_transitions("ECR", "reviewing")

    def test_eco_transitions(self):
        assert "implementing" in get_valid_transitions("ECO", "draft")
        assert "effective" in get_valid_transitions("ECO", "verified")
        assert "closed" in get_valid_transitions("ECO", "effective")

    def test_terminal_states(self):
        assert is_terminal("Project", "completed")
        assert is_terminal("ECR", "rejected")
        assert is_terminal("ECO", "closed")
        assert not is_terminal("ECR", "draft")

    def test_assert_transition_valid(self):
        assert_transition("ECR", "draft", "submitted")  # 不抛异常

    def test_assert_transition_invalid(self):
        with pytest.raises(TransitionError, match="终态"):
            assert_transition("ECR", "rejected", "draft")

    def test_assert_transition_unknown_model(self):
        with pytest.raises(TransitionError, match="未知模型"):
            assert_transition("Unknown", "a", "b")

    def test_invalid_from_to(self):
        with pytest.raises(TransitionError, match="不是合法转换"):
            assert_transition("ECR", "draft", "approved")  # 跳过 submitted


class TestSecurity:
    """安全中间件测试"""

    def test_sanitize_html_script(self):
        result = sanitize_html('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_html_img(self):
        result = sanitize_html('<img src=x onerror=alert(1)>')
        # HTML special chars <> are escaped
        assert "&lt;img" in result
        assert "1)&gt;" in result
        # But the attribute names themselves are not stripped — the purpose is
        # to prevent the entire tag from rendering, not to strip attributes

    def test_sanitize_html_safe(self):
        result = sanitize_html("Hello World")
        assert result == "Hello World"

    def test_sanitize_dict(self):
        data = {
            "name": "Normal User",
            "comment": "<script>alert(1)</script>",
            "nested": {"bio": "<img src=x>"},
            "tags": ["safe", "<script>bad</script>"],
        }
        sanitize_dict(data)
        assert "<script>" not in data["comment"]
        assert "<img" not in data["nested"]["bio"]
        assert "<script>" not in data["tags"][1]
        assert "Normal User" == data["name"]  # safe text unchanged
        assert "safe" == data["tags"][0]  # safe tag unchanged
