"""
统一状态机框架 — 集中管理 ROS 系统中所有业务模型的状态转换规则。

使用方式 (FastAPI 调用层):
    from app.services.state_machine import assert_transition, get_valid_transitions
    try:
        assert_transition("Project", "planning", "running")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

纯 Python 3.11+，不依赖 FastAPI / SQLAlchemy。
"""

from __future__ import annotations

from typing import List, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# 状态转换配置
# ═══════════════════════════════════════════════════════════════════════════════
# key   = 模型名（与 SQLAlchemy model __name__ 一致）
# value = {from_status: [to_status1, to_status2, ...]}
# 空列表表示终态，不再允许任何转换。

_TRANSITIONS_CONFIG: dict[str, dict[str, list[str]]] = {
    # ── Project ──────────────────────────────────────────────────────────────
    # 生命周期: 草稿 → 规划 → 执行 → 完成
    "Project": {
        "draft": ["planning"],
        "planning": ["running", "cancelled", "paused"],
        "running": ["completed", "cancelled", "paused"],
        "paused": ["running"],
        "completed": [],
        "cancelled": [],
    },

    # ── BOM ─────────────────────────────────────────────────────────────────
    # 物料清单: 草稿 → 发布 → 废止; 发布可退回草稿修订
    "BOM": {
        "draft": ["released"],
        "released": ["obsolete", "draft"],
        "obsolete": [],
    },

    # ── TestRequest ─────────────────────────────────────────────────────────
    # 测试申请: 草稿 → 提交 → 测试中 → 完成; 支持退稿和取消
    "TestRequest": {
        "draft": ["submitted", "cancelled"],
        "submitted": ["testing", "draft"],
        "testing": ["done", "cancelled"],
        "done": [],
        "cancelled": [],
    },

    # ── Certification ────────────────────────────────────────────────────────
    # 认证: 规划 → 准备 → 测试 → 提交 → 已获证; 任意状态可失败
    "Certification": {
        "planning": ["preparing", "failed"],
        "preparing": ["testing", "failed"],
        "testing": ["submitted", "failed"],
        "submitted": ["certified", "failed"],
        "certified": [],
        "failed": [],
    },

    # ── MQVerification ──────────────────────────────────────────────────────
    # 新物料验证: 待处理 → 测试中 → 通过/不通过
    "MQVerification": {
        "pending": ["testing"],
        "testing": ["pass", "fail"],
        "pass": [],
        "fail": [],
    },

    # ── QualityIssue ─────────────────────────────────────────────────────────
    # 品质整改: 开启 → 调查中 → 已解决 → 关闭; 开启可直接取消
    "QualityIssue": {
        "open": ["investigating", "cancelled"],
        "investigating": ["resolved"],
        "resolved": ["closed"],
        "closed": [],
        "cancelled": [],
    },

    # ── ECR ──────────────────────────────────────────────────────────────────
    # 工程变更请求: 草稿 → 提交 → 评审中 → 批准/驳回
    "ECR": {
        "draft": ["submitted"],
        "submitted": ["reviewing"],
        "reviewing": ["approved", "rejected"],
        "approved": [],
        "rejected": [],
    },

    # ── ECN ──────────────────────────────────────────────────────────────────
    # 工程变更通知: 草稿 → 提交 → 批准 → 已实施
    "ECN": {
        "draft": ["submitted"],
        "submitted": ["approved"],
        "approved": ["implemented"],
        "implemented": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════════════════════

def assert_transition(
    model_name: str,
    current_status: str,
    target_status: str,
) -> None:
    """验证从 current_status → target_status 是否合法。

    Raises:
        ValueError: 模型名不存在
        ValueError: 当前状态不存在于该模型的配置中
        ValueError: 目标状态不在允许的转换列表中
    """
    transitions = _get_model_transitions(model_name)
    allowed = transitions.get(current_status)
    if allowed is None:
        valid_states = list(transitions.keys())
        raise ValueError(
            f"'{model_name}' 不存在状态 '{current_status}'。"
            f" 有效状态: {valid_states}"
        )
    if target_status not in allowed:
        raise ValueError(
            f"'{model_name}' 不允许从 '{current_status}' 转换到 '{target_status}'。"
            f" 允许的目标状态: {allowed}"
        )


def get_valid_transitions(
    model_name: str,
    current_status: str,
) -> List[str]:
    """返回从当前状态出发的合法目标状态列表。

    Raises:
        ValueError: 模型名不存在
        ValueError: 当前状态不存在于该模型的配置中
    """
    transitions = _get_model_transitions(model_name)
    allowed = transitions.get(current_status)
    if allowed is None:
        valid_states = list(transitions.keys())
        raise ValueError(
            f"'{model_name}' 不存在状态 '{current_status}'。"
            f" 有效状态: {valid_states}"
        )
    return list(allowed)


def get_all_model_names() -> List[str]:
    """返回所有已注册的状态机模型名列表。"""
    return list(_TRANSITIONS_CONFIG.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 内部辅助
# ═══════════════════════════════════════════════════════════════════════════════

def _get_model_transitions(model_name: str) -> dict[str, list[str]]:
    """获取指定模型的转换字典，模型不存在时抛出 ValueError。"""
    transitions = _TRANSITIONS_CONFIG.get(model_name)
    if transitions is None:
        registered = list(_TRANSITIONS_CONFIG.keys())
        raise ValueError(
            f"未注册的模型名 '{model_name}'。"
            f" 已注册模型: {registered}"
        )
    return transitions
