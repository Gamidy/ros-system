"""P0 — 配置引擎 API: ConfigGroup + ConfigRule + 校验（关联表升级）"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.config_rule import ConfigGroup, ConfigRule
from app.models.feature import FeatureFamily
from app.schemas.config_engine import (
    ConfigGroupCreate, ConfigGroupOut,
    ConfigRuleCreate, ConfigRuleOut,
    ConfigValidateRequest, ConfigValidateResponse,
)

router = APIRouter(prefix="/config", tags=["配置引擎"])


# ── ConfigGroup ────────────────────────────

@router.post("/groups", response_model=ConfigGroupOut, status_code=201)
async def create_group(data: ConfigGroupCreate, db: AsyncSession = Depends(get_db),
                       _: User = Depends(get_current_user)):
    group = ConfigGroup(
        name=data.name,
        series_id=data.series_id,
    )

    # 绑定特征族（关联表）
    if data.family_ids:
        result = await db.execute(
            select(FeatureFamily).where(FeatureFamily.id.in_(data.family_ids))
        )
        families = list(result.scalars().all())
        group.families = families

    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.get("/groups", response_model=list[ConfigGroupOut])
async def list_groups(db: AsyncSession = Depends(get_db),
                      _: User = Depends(get_current_user)):
    result = await db.execute(
        select(ConfigGroup).options(selectinload(ConfigGroup.families))
    )
    return list(result.scalars().all())


# ── ConfigRule ────────────────────────────

@router.post("/rules", response_model=ConfigRuleOut, status_code=201)
async def create_rule(data: ConfigRuleCreate, db: AsyncSession = Depends(get_db),
                      _: User = Depends(get_current_user)):
    rule = ConfigRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/rules", response_model=list[ConfigRuleOut])
async def list_rules(db: AsyncSession = Depends(get_db),
                     _: User = Depends(get_current_user)):
    result = await db.execute(select(ConfigRule))
    return list(result.scalars().all())


# ── 配置校验 ──────────────────────────────

@router.post("/groups/{group_id}/validate", response_model=ConfigValidateResponse)
async def validate_config(
    group_id: int,
    data: ConfigValidateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = await db.get(ConfigGroup, group_id)
    if not group:
        raise HTTPException(404, "配置组不存在")

    rules_result = await db.execute(
        select(ConfigRule).where(ConfigRule.group_id == group_id)
    )
    rules = list(rules_result.scalars().all())

    violations = []
    selected = set(data.selected_option_ids)

    for rule in rules:
        src_in = rule.source_option_id in selected
        tgt_in = rule.target_option_id in selected

        if rule.rule_type == "requires":
            if src_in and not tgt_in:
                violations.append(
                    f"选项 {rule.source_option_id} 需要选项 {rule.target_option_id}"
                )
        elif rule.rule_type == "excludes":
            if src_in and tgt_in:
                violations.append(
                    f"选项 {rule.source_option_id} 与选项 {rule.target_option_id} 互斥"
                )

    return ConfigValidateResponse(
        valid=len(violations) == 0,
        violations=violations,
    )
