"""
状态转换查询API — 提供状态机规则的只读查询端点。
"""

from fastapi import APIRouter, HTTPException, Query

from app.services.state_machine import (
    _TRANSITIONS_CONFIG,
    get_all_model_names,
    get_valid_transitions,
)

router = APIRouter(tags=["状态转换查询"])


@router.get("/state-transitions")
def query_state_transitions(
    model: str = Query(..., description="模型名称"),
    current: str | None = Query(None, description="当前状态，为空时返回所有可能状态"),
) -> dict:
    """
    查询状态转换：根据模型名和当前状态，返回所有可能的下一状态及触发条件。

    - 如果 `current` 有值，返回从该状态出发的合法目标状态列表。
    - 如果 `current` 为空，返回该模型所有可能的状态（去重）。
    """
    if current:
        try:
            transitions = get_valid_transitions(model, current)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"model": model, "current": current, "transitions": transitions}
    else:
        # 返回该模型所有可能的状态（从_TRANSITIONS_CONFIG 提取所有状态值去重）
        model_config = _TRANSITIONS_CONFIG.get(model)
        if model_config is None:
            registered = list(_TRANSITIONS_CONFIG.keys())
            raise HTTPException(
                status_code=400,
                detail=f"未注册的模型名 '{model}'。已注册模型: {registered}",
            )
        all_states = sorted(set(model_config.keys()))
        return {"model": model, "current": None, "transitions": all_states}


@router.get("/state-models")
def list_state_models() -> dict:
    """返回所有已注册的状态机模型名列表。"""
    return {"models": get_all_model_names()}
