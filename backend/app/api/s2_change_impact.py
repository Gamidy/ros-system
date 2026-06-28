"""变更影响分析 API — Phase 6 S2

规则 CRUD + 记录列表/详情
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.permissions import require_menu
from app.core.security import require_role
from app.models.change_impact import ChangeImpactRecord, ChangeImpactRule
from app.schemas import (
    ChangeImpactRecordOut,
    ChangeImpactRuleCreate,
    ChangeImpactRuleUpdate,
    ChangeImpactRuleOut,
)


class ActionResponse(BaseModel):
    """简单操作响应"""
    success: bool
    message: str = ""

router = APIRouter(prefix="/api/s2/change-impact", tags=["S2-变更影响分析"])


# ═══════════════ 规则 CRUD ═══════════════


@router.get("/rules")
def list_impact_rules(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    name: str = Query("", description="规则名称模糊搜索"),
    trigger_type: str = Query("", description="触发类型过滤"),
    impact_level: str = Query("", description="影响等级过滤"),
    is_active: bool = Query(None, description="启用状态过滤"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "quality_engineer")),
) -> dict:
    """分页规则列表"""
    q = db.query(ChangeImpactRule)
    if name:
        q = q.filter(ChangeImpactRule.name.ilike(f"%{name}%"))
    if trigger_type:
        q = q.filter(ChangeImpactRule.trigger_type == trigger_type)
    if impact_level:
        q = q.filter(ChangeImpactRule.impact_level == impact_level)
    if is_active is not None:
        q = q.filter(ChangeImpactRule.is_active == is_active)

    total = q.count()
    items = (
        q.order_by(ChangeImpactRule.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # 手动序列化 ORM → dict 避免 PydanticResponse 序列化失败
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ChangeImpactRuleOut.model_validate(r).model_dump(mode="json") for r in items],
    }


@router.post("/rules", response_model=ChangeImpactRuleOut, status_code=201)
def create_impact_rule(
    data: ChangeImpactRuleCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "quality_engineer")),
) -> ChangeImpactRuleOut:
    """创建变更影响规则"""
    rule = ChangeImpactRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=ChangeImpactRuleOut)
def update_impact_rule(
    rule_id: int,
    data: ChangeImpactRuleUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "quality_engineer")),
) -> ChangeImpactRuleOut:
    """更新变更影响规则"""
    rule = db.query(ChangeImpactRule).filter(ChangeImpactRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
def delete_impact_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "quality_engineer")),
) -> dict:
    """删除变更影响规则"""
    rule = db.query(ChangeImpactRule).filter(ChangeImpactRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return {"id": rule_id, "success": True, "message": "删除成功"}


# ═══════════════ 记录查询（只读）═══════════════


@router.get("/records")
def list_impact_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    impact_level: str = Query("", description="影响等级过滤 critical/major/minor/none"),
    source_type: str = Query("", description="来源类型过滤 ecr/eco/prototype"),
    prototype_id: int = Query(0, description="按样机筛选"),
    ecr_id: int = Query(0, description="按ECR筛选"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-change-impact")),
) -> dict:
    """变更影响分析记录列表（分页+筛选）"""
    q = db.query(ChangeImpactRecord)
    if prototype_id:
        q = q.filter(ChangeImpactRecord.prototype_id == prototype_id)
    if impact_level:
        q = q.filter(ChangeImpactRecord.impact_level == impact_level)
    if source_type == "ecr":
        q = q.filter(ChangeImpactRecord.ecr_id.isnot(None))
    elif source_type == "eco":
        # ECO is tracked via the linked ECR; no direct eco_id on record yet
        q = q.filter(ChangeImpactRecord.ecr_id.isnot(None))
    elif source_type == "prototype":
        q = q.filter(ChangeImpactRecord.prototype_id.isnot(None),
                     ChangeImpactRecord.ecr_id.is_(None))
    if ecr_id > 0:
        q = q.filter(ChangeImpactRecord.ecr_id == ecr_id)

    total = q.count()
    items = (
        q.order_by(ChangeImpactRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ChangeImpactRecordOut.model_validate(r).model_dump(mode="json") for r in items],
    }


@router.get("/records/{record_id}", response_model=ChangeImpactRecordOut)
def get_impact_record(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("cert-change-impact")),
) -> ChangeImpactRecordOut:
    """变更影响分析记录详情"""
    record = db.query(ChangeImpactRecord).filter(ChangeImpactRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="影响分析记录不存在")
    return record


# ═══════════════ 统计 ═══════════════


@router.get("/stats")
def get_change_impact_stats(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "quality_engineer", "rd_director")),
) -> dict:
    """变更影响分析统计数据"""
    total_rules = db.query(ChangeImpactRule).count()
    active_rules = db.query(ChangeImpactRule).filter(ChangeImpactRule.is_active.is_(True)).count()
    total_records = db.query(ChangeImpactRecord).count()

    # — 按影响等级统计 (enum值 → high/medium/low) —
    level_map = {"critical": "high", "major": "medium", "minor": "low"}
    by_impact_level = {"high": 0, "medium": 0, "low": 0}
    rows = (
        db.query(ChangeImpactRecord.impact_level, func.count(ChangeImpactRecord.id))
        .group_by(ChangeImpactRecord.impact_level)
        .all()
    )
    for level, cnt in rows:
        key = level_map.get(level)
        if key:
            by_impact_level[key] += cnt

    # — 按来源类型统计 (从现有外键字段推导) —
    ecr_count = db.query(ChangeImpactRecord).filter(ChangeImpactRecord.ecr_id.isnot(None)).count()
    prototype_count = (
        db.query(ChangeImpactRecord).filter(ChangeImpactRecord.prototype_id.isnot(None)).count()
    )
    by_source_type = {"ecr": ecr_count, "eco": 0, "prototype": prototype_count}

    # — 最近10条记录 —
    recent = (
        db.query(ChangeImpactRecord)
        .order_by(ChangeImpactRecord.created_at.desc())
        .limit(10)
        .all()
    )
    recent_records = [ChangeImpactRecordOut.model_validate(r).model_dump(mode="json") for r in recent]

    return {
        "total_rules": total_rules,
        "active_rules": active_rules,
        "total_records": total_records,
        "by_impact_level": by_impact_level,
        "by_source_type": by_source_type,
        "recent_records": recent_records,
    }
