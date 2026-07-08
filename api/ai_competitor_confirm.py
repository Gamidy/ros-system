"""竞品 AI 导入 — 确认导入 & 历史查询

基于 LLMParamExtractor 的智能提取流程，用户确认后批量入库。

Endpoints:
- POST   /pm/ai-import/{session_id}/confirm — 确认导入
- GET    /pm/ai-import/history               — 导入历史
"""
import io
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.competitor import CompetitorModel
from app.schemas.ai_competitor_import import (
    ImportSourceType,
    AIExtractedField,
    CompetitorExtraction,
    AICompetitorConfirmRequest,
    AICompetitorConfirmResponse,
    AIImportSessionSummary,
    AIImportHistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pm/ai-import",
    tags=["竞品AI导入"],
)

# ── 内存会话存储（共享于 ai_competitor_import 的 _sessions）──
# 从主模块引入内存会话
from app.api.ai_competitor_import import _sessions, _resolve_market_code


def _build_session_summary(
    session_id: str,
    session: dict[str, Any],
) -> AIImportSessionSummary:
    """从会话数据构建摘要"""
    extractions = session.get("extractions")
    total_extracted = len(extractions) if extractions else 0
    return AIImportSessionSummary(
        session_id=session_id,
        source_type=session["source_type"],
        target_market_id=session["target_market_id"],
        created_at=session.get("created_at", datetime.now(timezone.utc)),
        total_extracted=total_extracted,
        total_imported=session.get("total_imported", 0),
        total_skipped=session.get("total_skipped", 0),
        status=session.get("status", "parsing"),
    )


# ═══════════════════════════════════════════════════════════════════════
# 字段解析辅助
# ═══════════════════════════════════════════════════════════════════════


def _get_field_value(field: AIExtractedField) -> Optional[str]:
    """从 AIExtractedField 获取值"""
    return field.value


def _parse_int_field(value: Optional[str], factor: float = 1.0) -> Optional[int]:
    """解析字符串为 int，可选乘系数

    Args:
        value:  字符串值
        factor: 乘系数（如 kW→W: 1000, BTU→W: 0.293）

    Returns:
        int | None
    """
    if value is None:
        return None
    try:
        return int(round(float(value) * factor))
    except (ValueError, TypeError):
        return None


def _parse_float_field(value: Optional[str]) -> Optional[float]:
    """解析字符串为 float"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════════════════


@router.post("/{session_id}/confirm", response_model=AICompetitorConfirmResponse)
def confirm_import(
    session_id: str,
    body: AICompetitorConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> AICompetitorConfirmResponse:
    """确认导入 — 将选中的 AI 提取结果写入竞品库

    用户可以对每条提取结果选择 import / skip，
    并提交 overrides（字段覆盖）修正错误提取。
    """
    # ── 校验会话 ──
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if session["status"] not in ("preview",):
        raise HTTPException(
            status_code=400,
            detail=f"会话状态不允许确认 (当前状态: {session['status']})",
        )

    extractions: list[CompetitorExtraction] = session.get("extractions") or []
    if not extractions:
        raise HTTPException(status_code=400, detail="没有可确认的提取结果")

    # ── 校验确认列表 ──
    confirm_map: dict[int, dict] = {}
    for item in body.confirmations:
        if item.extraction_index < 0 or item.extraction_index >= len(extractions):
            raise HTTPException(
                status_code=400,
                detail=f"提取索引越界: {item.extraction_index} (有效范围: 0-{len(extractions)-1})",
            )
        confirm_map[item.extraction_index] = {
            "action": item.action,
            "overrides": item.overrides,
        }

    # ── 执行导入 ──
    imported_ids: list[int] = []
    failures: list[dict] = []
    imported_count = 0
    skipped_count = 0

    # 从会话获取市场代码
    target_market_id = session.get("target_market_id")
    market_code = ""
    if target_market_id:
        try:
            market_code = _resolve_market_code(db, target_market_id)
        except HTTPException:
            market_code = ""
    for idx, extraction in enumerate(extractions):
        if idx in confirm_map:
            item = confirm_map[idx]
        else:
            # 未在确认列表中的跳过
            item = {"action": "skip", "overrides": []}

        if item["action"] == "skip":
            skipped_count += 1
            continue

        # ── action == "import" ──
        try:
            competitor = CompetitorModel()

            # 从提取结果填入 CompetitorModel
            competitor.brand = _get_field_value(extraction.brand)
            competitor.model = _get_field_value(extraction.model)
            competitor.product_type = _get_field_value(extraction.product_type)
            competitor.market = market_code

            # 数值字段
            competitor.cooling_capacity_w = _parse_int_field(
                _get_field_value(extraction.capacity_kw), factor=1000,
            )
            competitor.heating_capacity_w = _parse_int_field(
                _get_field_value(extraction.heating_capacity_btu), factor=1 / 3.412,
            )
            competitor.eer = _parse_float_field(
                _get_field_value(extraction.eer),
            )
            competitor.noise_indoor_db = _parse_float_field(
                _get_field_value(extraction.indoor_noise_db),
            )
            competitor.noise_outdoor_db = _parse_float_field(
                _get_field_value(extraction.outdoor_noise_db),
            )
            competitor.energy_rating = _get_field_value(extraction.energy_label)
            competitor.factory_price = _get_field_value(extraction.price)

            # 应用用户覆盖
            for override in item["overrides"]:
                field_name = override.get("field")
                value = override.get("value")
                if field_name and hasattr(competitor, field_name):
                    setattr(competitor, field_name, value)

            # 必填校验
            if not competitor.brand or not competitor.model:
                failures.append({
                    "index": idx,
                    "reason": "品牌或型号为空，无法导入",
                })
                skipped_count += 1
                continue

            db.add(competitor)
            db.flush()
            db.refresh(competitor)
            imported_ids.append(competitor.id)
            imported_count += 1
        except Exception as exc:
            logger.warning("确认导入第 %d 条失败: %s", idx, exc)
            failures.append({
                "index": idx,
                "reason": str(exc),
            })
            skipped_count += 1

    if imported_ids:
        db.commit()

    # ── 更新会话状态 ──
    session["status"] = "completed"
    session["total_imported"] = imported_count
    session["total_skipped"] = skipped_count

    logger.info(
        "AI导入确认完成: session_id=%s, imported=%d, skipped=%d",
        session_id, imported_count, skipped_count,
    )

    return AICompetitorConfirmResponse(
        session_id=session_id,
        total_confirmed=len(body.confirmations),
        total_imported=imported_count,
        total_skipped=skipped_count,
        imported_ids=imported_ids,
        failures=failures,
    )


@router.get("/history", response_model=AIImportHistoryResponse)
def list_import_history(
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> AIImportHistoryResponse:
    """获取 AI 导入历史"""
    # 按创建时间倒序排列
    sorted_sessions = sorted(
        _sessions.items(),
        key=lambda kv: kv[1].get("created_at", datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    sessions = [
        _build_session_summary(sid, data)
        for sid, data in sorted_sessions[:limit]
    ]
    return AIImportHistoryResponse(
        sessions=sessions,
        total=len(sessions),
    )
