"""ECO API模块 — 工程变更指令 CRUD + 状态转换 + 变更看板（明细项管理已拆分到 eco_items.py）"""
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.core.enums import ECOStatus
from app.models.user import User
from app.models.ecr_eco import ECO, ECOItem, ECRRequest
from app.schemas import (
    ECOCreate, ECOUpdate, ECOOut, ECODetailOut,
    ECOItemCreate, ECOItemUpdate, ECOItemOut,
    ECOChDashboardOut,
)

router = APIRouter(prefix="/eco", tags=["ECO"])

logger = logging.getLogger(__name__)


# ── EventStore 辅助 ──────────────────────────────────────────────


def _record_event_store(db, event_type, aggregate_type, aggregate_id, event_data=None, correlation_id=None):
    """非阻断记录事件到 EventStore"""
    try:
        from app.services.event_store_service import EventStoreService
        EventStoreService.record(
            db=db,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            event_data=event_data or {},
            producer=f"{aggregate_type}.api",
        )
    except Exception as e:
        logger.warning("EventStore record 失败 (%s/%s#%s): %s", event_type, aggregate_type, aggregate_id, e)


# ══════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════

def _gen_eco_code(db: Session) -> str:
    """生成ECO编号: ECO-YYYYMMDD-XXXX (每日自增序号)"""
    today_str = date.today().strftime("%Y%m%d")
    prefix = f"ECO-{today_str}-"
    last = (
        db.query(ECO)
        .filter(ECO.code.like(f"{prefix}%"))
        .order_by(ECO.code.desc())
        .first()
    )
    seq = (int(last.code[-4:]) + 1) if last else 1
    return f"{prefix}{seq:04d}"


def _get_eco_or_404(db: Session, eco_id: int) -> ECO:
    """按ID查找ECO，不存在则404"""
    eco = db.query(ECO).filter(ECO.id == eco_id).first()
    if not eco:
        raise HTTPException(status_code=404, detail="ECO不存在")
    return eco


def _check_status(eco: ECO, allowed: list[str], action: str = "操作"):
    """检查ECO当前状态是否允许指定操作"""
    if eco.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"ECO当前状态为'{eco.status}'，不允许{action}（允许: {'/'.join(allowed)}）",
        )


def _count_items(db: Session, eco_id: int) -> int:
    """查询ECO的明细项数量"""
    return db.query(func.count(ECOItem.id)).filter(ECOItem.eco_id == eco_id).scalar() or 0


def _eco_to_out(eco: ECO, db: Optional[Session] = None) -> dict:
    """ECO ORM对象 → ECOOut dict"""
    return {
        "id": eco.id,
        "code": eco.code,
        "ecr_id": eco.ecr_id,
        "title": eco.title,
        "change_summary": eco.change_summary,
        "implementation_plan": eco.implementation_plan,
        "effective_date": eco.effective_date,
        "status": eco.status,
        "created_by": eco.created_by,
        "verified_by": eco.verified_by,
        "verified_at": eco.verified_at,
        "closed_by": eco.closed_by,
        "closed_at": eco.closed_at,
        "org_id": eco.org_id,
        "created_at": eco.created_at,
        "updated_at": eco.updated_at,
        "item_count": _count_items(db, eco.id) if db else (len(eco.items) if hasattr(eco, "items") and eco.items else 0),
    }


def _eco_to_detail(eco: ECO, db: Session) -> dict:
    """ECO ORM对象 → ECODetailOut dict（含明细项+关联ECR信息）"""
    items_out = []
    for item in (eco.items or []):
        items_out.append({
            "id": item.id,
            "eco_id": item.eco_id,
            "seq": item.seq,
            "change_type": item.change_type,
            "object_type": item.object_type,
            "object_id": item.object_id,
            "object_code": item.object_code,
            "object_name": item.object_name,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "description": item.description,
            "created_at": item.created_at,
        })

    base = _eco_to_out(eco, db)
    base["items"] = items_out
    base["ecr_code"] = eco.ecr.code if eco.ecr else None
    base["ecr_title"] = eco.ecr.title if eco.ecr else None
    return base


def _item_to_out(item: ECOItem) -> dict:
    """ECOItem ORM对象 → ECOItemOut dict"""
    return {
        "id": item.id,
        "eco_id": item.eco_id,
        "seq": item.seq,
        "change_type": item.change_type,
        "object_type": item.object_type,
        "object_id": item.object_id,
        "object_code": item.object_code,
        "object_name": item.object_name,
        "old_value": item.old_value,
        "new_value": item.new_value,
        "description": item.description,
        "created_at": item.created_at,
    }


# ══════════════════════════════════════════════════
# 变更看板（必须在 /{eco_id} 路由之前定义）
# ══════════════════════════════════════════════════

@router.get("/changes", response_model=ECOChDashboardOut)
def eco_changes_dashboard(
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOChDashboardOut:
    """ECO变更看板: 按状态统计 + 按类型分布 + 本月新增 + 待验证 + 最近变更"""
    # 按状态统计
    status_rows = db.query(ECO.status, func.count(ECO.id)).group_by(ECO.status).all()
    status_summary = {row[0]: row[1] for row in status_rows}

    # 按变更类型分布（从ECOItem的change_type统计）
    type_rows = db.query(ECOItem.change_type, func.count(ECOItem.id)).group_by(ECOItem.change_type).all()
    type_distribution = {row[0]: row[1] for row in type_rows}

    # 本月新增
    first_day = date.today().replace(day=1)
    this_month_new = (
        db.query(func.count(ECO.id))
        .filter(cast(ECO.created_at, Date) >= first_day)
        .scalar()
    ) or 0

    # 待验证（IMPLEMENTING状态的ECO）
    pending_verification = (
        db.query(func.count(ECO.id))
        .filter(ECO.status == ECOStatus.IMPLEMENTING.value)
        .scalar()
    ) or 0

    # 最近10条变更
    recent = (
        db.query(ECO)
        .order_by(ECO.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "status_summary": status_summary,
        "type_distribution": type_distribution,
        "this_month_new": this_month_new,
        "pending_verification": pending_verification,
        "changes": [_eco_to_out(eco, db) for eco in recent],
    }


# ══════════════════════════════════════════════════
# ECO CRUD
# ══════════════════════════════════════════════════

@router.get("", response_model=list[ECOOut])
def list_ecos(
    status: Optional[str] = Query(None, description="按状态过滤"),
    keyword: Optional[str] = Query(None, description="按标题/编号/摘要搜索"),
    date_from: Optional[date] = Query(None, description="起始日期(created_at)"),
    date_to: Optional[date] = Query(None, description="截止日期(created_at)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> list[ECOOut]:
    """ECO列表查询 — 支持状态/关键词/日期范围过滤及分页"""
    q = db.query(ECO)

    if status:
        q = q.filter(ECO.status == status)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            ECO.code.ilike(kw)
            | ECO.title.ilike(kw)
            | ECO.change_summary.ilike(kw),
        )
    if date_from:
        q = q.filter(cast(ECO.created_at, Date) >= date_from)
    if date_to:
        q = q.filter(cast(ECO.created_at, Date) <= date_to)

    items = (
        q.order_by(ECO.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [_eco_to_out(eco, db) for eco in items]


@router.post("", response_model=ECOOut, status_code=201)
def create_eco(
    data: ECOCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """创建ECO — 自动生成编号，可同时创建明细项"""
    # 校验关联ECR
    if data.ecr_id is not None:
        ecr = db.query(ECRRequest).filter(ECRRequest.id == data.ecr_id).first()
        if not ecr:
            raise HTTPException(status_code=404, detail="关联ECR不存在")

    code = _gen_eco_code(db)

    eco = ECO(
        code=code,
        ecr_id=data.ecr_id,
        title=data.title,
        change_summary=data.change_summary,
        implementation_plan=data.implementation_plan,
        effective_date=data.effective_date,
        status=ECOStatus.DRAFT.value,
        created_by=current_user.id,
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(eco)
    db.flush()

    # 批量创建明细项
    for idx, item in enumerate(data.items or []):
        db.add(ECOItem(
            eco_id=eco.id,
            seq=idx + 1,
            change_type=item.change_type,
            object_type=item.object_type,
            object_id=item.object_id,
            object_code=item.object_code,
            object_name=item.object_name,
            old_value=item.old_value,
            new_value=item.new_value,
            description=item.description,
            org_id=getattr(current_user, "org_id", None),
        ))

    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.get("/{eco_id}", response_model=ECODetailOut)
def get_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECODetailOut:
    """获取ECO详情 — 含明细项列表 + 关联ECR信息"""
    eco = (
        db.query(ECO)
        .options(joinedload(ECO.items), joinedload(ECO.ecr))
        .filter(ECO.id == eco_id)
        .first()
    )
    if not eco:
        raise HTTPException(status_code=404, detail="ECO不存在")
    return _eco_to_detail(eco, db)


@router.put("/{eco_id}", response_model=ECOOut)
def update_eco(
    eco_id: int,
    data: ECOUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """更新ECO基本信息 — 仅DRAFT状态允许"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value], "更新")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(eco, key, val)
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)


@router.delete("/{eco_id}", status_code=204)
def delete_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> None:
    """删除ECO — 仅DRAFT状态允许（级联删除明细项）"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value], "删除")
    db.delete(eco)
    db.commit()


# ══════════════════════════════════════════════════
# 状态转换
# ══════════════════════════════════════════════════

@router.post("/{eco_id}/implement", response_model=ECOOut)
def implement_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """开始实施: DRAFT → IMPLEMENTING"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.DRAFT.value], "开始实施")
    eco.status = ECOStatus.IMPLEMENTING.value
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)

    # ── EventStore 记录 ──
    _record_event_store(db, "eco.implementing", "eco", eco.id,
                        event_data={"code": eco.code, "title": eco.title})

    return _eco_to_out(eco, db)


@router.post("/{eco_id}/verify", response_model=ECOOut)
def verify_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """验证通过: IMPLEMENTING → VERIFIED，记录验证人/验证时间"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.IMPLEMENTING.value], "验证")
    now = datetime.now(timezone.utc)
    eco.status = ECOStatus.VERIFIED.value
    eco.verified_by = current_user.id
    eco.verified_at = now
    eco.updated_at = now
    db.commit()
    db.refresh(eco)

    # ── EventStore 记录 ──
    _record_event_store(db, "eco.verified", "eco", eco.id,
                        event_data={"code": eco.code})

    return _eco_to_out(eco, db)


# ── ECO成本重算联动 ──────────────────────────────────────


def _trigger_cost_recalc_on_eco(eco: ECO, db: Session) -> None:
    """ECO生效后自动触发冷量联动成本重算（非阻断）

    从ECR的affected_products 字段获取产品策划ID列表，
    对每个产品策划调用 run_capacity_recalculation。
    """
    if not eco.ecr_id:
        logger.info("ECO %s: 无关联ECR，跳过成本重算", eco.id)
        return

    import json
    ecr = eco.ecr
    if not ecr or not ecr.affected_products:
        logger.info("ECO %s: ECR %s 无 affected_products，跳过成本重算", eco.id, eco.ecr_id)
        return

    # 解析产品策划ID列表
    products = ecr.affected_products
    if isinstance(products, str):
        try:
            products = json.loads(products)
        except (json.JSONDecodeError, TypeError):
            logger.warning("ECO %s: affected_products 解析失败: %s", eco.id, products)
            return

    if not isinstance(products, list):
        products = [products]

    plan_ids: list[str] = []
    for p in products:
        if isinstance(p, dict):
            pid = p.get("product_plan_id") or p.get("id")
            if pid:
                plan_ids.append(str(pid))
        elif isinstance(p, (int, str)):
            plan_ids.append(str(p))

    if not plan_ids:
        logger.info("ECO %s: 未找到有效的产品策划ID，跳过成本重算", eco.id)
        return

    # 获取用户名
    user_name = None
    if hasattr(eco, 'creator') and eco.creator:
        user_name = getattr(eco.creator, 'name', None) or getattr(eco.creator, 'username', None)

    # 对每个产品策划触发重算
    from app.services.capacity_recalc_service import run_capacity_recalculation
    success_count = 0
    for pid in set(plan_ids):  # 去重
        try:
            result = run_capacity_recalculation(
                product_plan_id=pid,
                trigger_source="eco",
                user_name=user_name,
                db=db,
            )
            logger.info("ECO %s: 产品策划 %s 成本重算完成, 效率评分=%s",
                        eco.id, pid, result.get("result", {}).get("cost_efficiency_score", "N/A"))
            success_count += 1
        except Exception as e:
            logger.warning("ECO %s: 产品策划 %s 成本重算失败(跳过): %s", eco.id, pid, e)

    if success_count > 0:
        # 刷新ECO以持久化变更
        db.flush()

    logger.info("ECO %s: 成本重算联动完成, 成功=%d/总=%d", eco.id, success_count, len(set(plan_ids)))


@router.post("/{eco_id}/effective", response_model=ECOOut)
def effective_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """生效: VERIFIED → EFFECTIVE，触发 BOM 更新（Celery 异步重试队列）
    Board 裁决: BOM Update → Retry(3次) → ROLLBACK_REQUIRED"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.VERIFIED.value], "生效")
    eco.status = ECOStatus.EFFECTIVE.value
    eco.updated_at = datetime.now(timezone.utc)

    # ── BOM Impact Propagation: 变更影响传播 ──
    try:
        from app.services.change_impact_engine import ChangeImpactEngine
        impact_result = ChangeImpactEngine(db).analyze_by_eco(eco_id)
        logger.info("ECO %s: 变更影响分析完成, 等级=%s, 记录=%d条",
                     eco_id, impact_result.get("overall_impact_level"),
                     len(impact_result.get("impact_records", [])))
    except Exception as e:
        logger.warning("ECO %s: 变更影响分析失败(非阻断): %s", eco_id, e)

    # ── BOM 联动: 触发 Celery 异步重试任务 ──
    try:
        from app.workers.bom_worker import eco_effective_bom_update
        eco_effective_bom_update.delay(eco_id)
        logger.info("ECO %s: BOM 更新任务已投递到 Celery 队列", eco_id)
    except Exception as e:
        logger.warning("ECO %s: BOM 更新任务投递失败（Celery 可能未运行）: %s", eco_id, e)

    # ── 自动触发冷量联动成本重算（非阻断） ──
    try:
        _trigger_cost_recalc_on_eco(eco, db)
    except Exception as e:
        logger.warning("ECO %s: 成本重算触发失败(非阻断): %s", eco_id, e)

    db.commit()
    db.refresh(eco)

    # ── EventStore 记录 ──
    _record_event_store(db, "eco.effective", "eco", eco.id,
                        event_data={"code": eco.code})

    return _eco_to_out(eco, db)


@router.post("/{eco_id}/rollback", response_model=ECOOut)
def rollback_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """回滚: EFFECTIVE → ROLLBACK_REQUIRED（Board 裁决 BOM更新失败补偿状态）
    触发 Saga 补偿: revert BOM → notify engineering"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.EFFECTIVE.value], "回滚")

    # ── Saga 补偿 ──
    try:
        from app.services.eco_bom_service import rollback_bom_update
        rollback_bom_update(eco_id)
    except Exception as e:
        logger.error("ECO %s: Saga 补偿失败: %s", eco_id, e)

    eco.status = ECOStatus.ROLLBACK_REQUIRED.value
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)

    # emit event
    try:
        from app.services.events import bus, EventTypes
        bus.emit(
            EventTypes.ECO_ROLLBACK_REQUIRED,
            eco_id=eco.id,
            eco_code=eco.code,
            title=eco.title,
        )
    except Exception as e:
        logger.warning("emit eco.rollback_required 失败: %s", e)

    return _eco_to_out(eco, db)


@router.post("/{eco_id}/close", response_model=ECOOut)
def close_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """关闭: EFFECTIVE → CLOSED，记录关闭人/关闭时间"""
    eco = _get_eco_or_404(db, eco_id)
    _check_status(eco, [ECOStatus.EFFECTIVE.value], "关闭")
    now = datetime.now(timezone.utc)
    eco.status = ECOStatus.CLOSED.value
    eco.closed_by = current_user.id
    eco.closed_at = now
    eco.updated_at = now
    db.commit()
    db.refresh(eco)

    # ── EventStore 记录 ──
    _record_event_store(db, "eco.closed", "eco", eco.id,
                        event_data={"code": eco.code})

    return _eco_to_out(eco, db)


@router.post("/{eco_id}/cancel", response_model=ECOOut)
def cancel_eco(
    eco_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("changes")),
) -> ECOOut:
    """取消: 任意状态 → CANCELLED（已关闭/已取消状态的ECO不可取消）"""
    eco = _get_eco_or_404(db, eco_id)
    if eco.status in (ECOStatus.CLOSED.value, ECOStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail=f"ECO已处于'{eco.status}'状态，无法取消")
    eco.status = ECOStatus.CANCELLED.value
    eco.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(eco)
    return _eco_to_out(eco, db)
# ── 明细项管理已拆分到 eco_items.py ──
