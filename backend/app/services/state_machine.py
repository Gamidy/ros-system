"""Phase 2.2 — 统一状态机框架

集中管理 PLM 系统中所有业务模型的状态转换规则，参考 ROS 系统设计。

使用方式:
    from app.services.state_machine import assert_transition, get_valid_transitions
    assert_transition("Project", "draft", "planning")
    # 无效转换 → ValueError

纯 Python，不依赖 FastAPI / SQLAlchemy。
"""

from __future__ import annotations
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════
# 状态转换配置
# ═══════════════════════════════════════════════════════

_TRANSITIONS: Dict[str, Dict[str, List[str]]] = {
    # ── Project ────────────────────────────────────
    "Project": {
        "draft": ["planning"],
        "planning": ["running", "cancelled", "paused"],
        "running": ["completed", "cancelled", "paused"],
        "paused": ["running"],
        "completed": [],
        "cancelled": [],
    },

    # ── BOM ───────────────────────────────────────
    "BOM": {
        "draft": ["released"],
        "released": ["obsolete", "draft"],
        "obsolete": [],
    },

    # ── ECR ───────────────────────────────────────
    "ECR": {
        "draft": ["submitted"],
        "submitted": ["approved", "rejected"],
        "approved": ["converted"],
        "rejected": [],
        "converted": [],
    },

    # ── ECO ───────────────────────────────────────
    "ECO": {
        "draft": ["implementing", "cancelled"],
        "implementing": ["verified", "cancelled"],
        "verified": ["effective", "cancelled"],
        "effective": ["closed", "cancelled"],
        "closed": [],
        "cancelled": [],
    },

    # ── Task ──────────────────────────────────────
    "Task": {
        "pending": ["in_progress", "cancelled"],
        "in_progress": ["done", "blocked", "cancelled"],
        "blocked": ["in_progress", "cancelled"],
        "done": [],
        "cancelled": [],
    },

    # ── Gate ──────────────────────────────────────
    "Gate": {
        "pending": ["passed", "failed", "skipped"],
        "passed": [],
        "failed": [],
        "skipped": [],
    },
}


class TransitionError(ValueError):
    """状态转换异常"""
    pass


def assert_transition(model_name: str, from_status: str, to_status: str) -> None:
    """校验状态转换合法性，不合法时抛出 TransitionError

    Args:
        model_name: 模型名称（如 'Project', 'ECR'）
        from_status: 当前状态
        to_status: 目标状态

    Raises:
        TransitionError: 转换不合法
    """
    config = _TRANSITIONS.get(model_name)
    if not config:
        raise TransitionError(f"未知模型: {model_name}")

    allowed = get_valid_transitions(model_name, from_status)
    if to_status not in allowed:
        if not allowed:
            detail = f"'{from_status}' 是终态，不可再转换"
        else:
            detail = (
                f"'{from_status}' → '{to_status}' 不是合法转换，"
                f"允许: {allowed}"
            )
        raise TransitionError(detail)


def get_valid_transitions(model_name: str, from_status: str) -> List[str]:
    """获取指定模型/状态的合法目标状态列表

    Args:
        model_name: 模型名称
        from_status: 当前状态

    Returns:
        允许转换到的状态列表（空列表 = 终态）
    """
    config = _TRANSITIONS.get(model_name)
    if not config:
        return []
    return config.get(from_status, [])


def is_terminal(model_name: str, status: str) -> bool:
    """判断是否为终态"""
    return get_valid_transitions(model_name, status) == []


def list_models() -> List[str]:
    """列出所有已注册的模型"""
    return list(_TRANSITIONS.keys())


def get_model_transitions(model_name: str) -> Optional[Dict[str, List[str]]]:
    """获取模型的完整状态转换配置"""
    return _TRANSITIONS.get(model_name)


# ── 便捷函数 ────────


def guard_transition(model_name: str, from_status: str, to_status: str, action: str = "操作"):
    """FastAPI 风格的状态转换校验，抛出 HTTPException"""
    from fastapi import HTTPException
    try:
        assert_transition(model_name, from_status, to_status)
    except TransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
