"""ProductPlan 版本管理 + 批量操作 API

从 product_plan.py 提取版本历史和批量操作端点到独立模块。
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductPlan, ProductPlanStage, Cost, CostType, ProductPlanProjectLink, ProductPlanHistory
from app.models.product_plan_subs import ProductPlanInitiation, ProductPlanTeam
from app.api.product_plan_schemas import _plan_to_dict, PlanCreate
from app.services.product_plan_workflow import create_product_plan as workflow_create
from app.models.plan_template import PlanTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/product-plans", tags=["产品策划-版本管理"])


# ── 版本历史端点 ──


@router.get("/{plan_id}/versions")
def list_plan_versions(
    plan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """产品策划版本历史列表"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    try:
        q = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id
        ).order_by(ProductPlanHistory.version.desc())
        total = q.count()
        versions = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [
                {"version": v.version, "changed_by": v.changed_by,
                 "changed_at": str(v.changed_at) if v.changed_at else None}
                for v in versions
            ],
            "total": total, "page": page, "page_size": page_size,
            "current_version": plan.version,
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"查询版本历史失败: {str(e)}")


@router.get("/{plan_id}/versions/{version}")
def get_plan_version_snapshot(
    plan_id: str,
    version: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """获取策划指定版本的完整数据快照"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    try:
        history = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id,
            ProductPlanHistory.version == version,
        ).first()
        if not history:
            raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")
        snapshot = json.loads(history.snapshot)
        return {
            "version": history.version, "snapshot": snapshot,
            "changed_by": history.changed_by,
            "changed_at": str(history.changed_at) if history.changed_at else None,
        }
    except HTTPException:
        raise
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"快照数据解析失败: {str(e)}")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"查询版本快照失败: {str(e)}")


FIELD_LABELS: dict[str, str] = {
    "name": "策划名称", "series": "产品系列", "market": "目标市场",
    "target_market_detail": "目标市场(详细)", "competitor_id": "竞品关联ID",
    "cost_target": "成本目标", "performance_target": "技术指标目标",
    "status": "流程阶段", "org_id": "所属组织", "created_by": "创建者", "version": "版本号",
}
SKIP_FIELDS: set[str] = {"id", "created_at", "updated_at"}


@router.get("/{plan_id}/versions/diff")
def diff_plan_versions(
    plan_id: str,
    version_a: int = Query(..., description="版本A（旧版本）"),
    version_b: int = Query(..., description="版本B（新版本）"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """比较两个版本的策划快照，返回字段级差异列表。"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    try:
        ha = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id,
            ProductPlanHistory.version == version_a,
        ).first()
        hb = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id,
            ProductPlanHistory.version == version_b,
        ).first()
        if not ha:
            raise HTTPException(status_code=404, detail=f"版本 {version_a} 不存在")
        if not hb:
            raise HTTPException(status_code=404, detail=f"版本 {version_b} 不存在")
        snap_a: dict = json.loads(ha.snapshot)
        snap_b: dict = json.loads(hb.snapshot)
        all_keys: set[str] = set(snap_a.keys()) | set(snap_b.keys())
        changes: list[dict] = []
        for key in sorted(all_keys):
            if key in SKIP_FIELDS:
                continue
            val_a = snap_a.get(key)
            val_b = snap_b.get(key)
            if val_a == val_b:
                continue
            if val_a is None and val_b is not None:
                change_type = "added"
            elif val_a is not None and val_b is None:
                change_type = "removed"
            else:
                change_type = "modified"
            changes.append({
                "field": key, "label": FIELD_LABELS.get(key, key),
                "type": change_type, "old_value": val_a, "new_value": val_b,
            })
        return {"version_a": version_a, "version_b": version_b, "changes": changes}
    except HTTPException:
        raise
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"快照数据解析失败: {str(e)}")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"查询版本快照失败: {str(e)}")


@router.post("/{plan_id}/versions/{version}/rollback")
def rollback_plan_version(
    plan_id: str,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> dict:
    """回滚到指定历史版本。"""
    plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="策划不存在")
    if current_user.role not in ("admin", "general_manager") and plan.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="只能回滚自己创建的策划")
    try:
        history = db.query(ProductPlanHistory).filter(
            ProductPlanHistory.product_plan_id == plan_id,
            ProductPlanHistory.version == version,
        ).first()
        if not history:
            raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")
        snapshot: dict = json.loads(history.snapshot)
        ROLLBACK_FIELDS: set[str] = {
            "name", "series", "market", "target_market_detail",
            "competitor_id", "cost_target", "performance_target", "status",
        }
        for key, val in snapshot.items():
            if key in ROLLBACK_FIELDS and val is not None:
                setattr(plan, key, val)
        plan.updated_at = func.now()
        plan._change_user = current_user.username
        db.commit()
        db.refresh(plan)
        return _plan_to_dict(plan)
    except HTTPException:
        raise
    except (json.JSONDecodeError, TypeError) as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"快照数据解析失败: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


# ── 批量操作 ──


class BatchCloneRequest(BaseModel):
    plan_ids: list[str]


class TemplateBatchItem(BaseModel):
    template_id: str
    count: int = 1


class BatchCreateRequest(BaseModel):
    templates: list[TemplateBatchItem]


@router.post("/batch-clone", status_code=201)
def batch_clone_plans(
    data: BatchCloneRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> list[dict]:
    """批量策划克隆。"""
    if not data.plan_ids:
        raise HTTPException(status_code=400, detail="plan_ids 不能为空")
    new_plans: list[dict] = []
    for plan_id in data.plan_ids:
        try:
            plan = db.query(ProductPlan).options(
                selectinload(ProductPlan.initiation),
            ).filter(ProductPlan.id == plan_id).first()
            if not plan:
                continue
            clone_data = {
                "name": f"{plan.name}-副本", "series": plan.series,
                "market": plan.market, "competitor_id": plan.competitor_id,
                "cost_target": plan.cost_target, "performance_target": plan.performance_target,
                "product_type": plan.initiation.product_type if plan.initiation else None,
                "market_id": None,
            }
            new_plan = workflow_create(db, clone_data, current_user.username)
            new_plans.append(_plan_to_dict(new_plan))
        except Exception as e:
            logger.warning("克隆策划 %s 失败: %s", plan_id, str(e))
            continue
    if not new_plans:
        raise HTTPException(status_code=400, detail="没有可克隆的策划")
    from app.services.ws_push import trigger_dashboard_refresh_sync
    trigger_dashboard_refresh_sync()
    return new_plans


@router.post("/batch-create", status_code=201)
def batch_create_plans(
    data: BatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> list[dict]:
    """按模板批量创建策划。"""
    if not data.templates:
        raise HTTPException(status_code=400, detail="templates 不能为空")
    new_plans: list[dict] = []
    for item in data.templates:
        try:
            template = db.query(PlanTemplate).filter(
                PlanTemplate.id == item.template_id,
                PlanTemplate.is_active == True,
            ).first()
            if not template:
                logger.warning("模板 %s 不存在或已停用，跳过", item.template_id)
                continue
            preset = template.preset_fields or {}
            base_name = preset.get("name") or template.name
            product_type = preset.get("product_type") or template.product_type
            for i in range(item.count):
                name = f"{base_name}-{i + 1}" if item.count > 1 else base_name
                create_data = {
                    "name": name, "series": preset.get("series"),
                    "market": template.market, "product_type": product_type,
                    "cost_target": preset.get("cost_target"),
                    "performance_target": preset.get("performance_target"),
                    "competitor_id": preset.get("competitor_id"),
                    "market_id": preset.get("market_id"),
                }
                new_plan = workflow_create(db, create_data, current_user.username)
                new_plans.append(_plan_to_dict(new_plan))
        except Exception as e:
            logger.warning("按模板 %s 批量创建失败: %s", item.template_id, str(e))
            continue
    if not new_plans:
        raise HTTPException(status_code=400, detail="没有成功创建的策划")
    from app.services.ws_push import trigger_dashboard_refresh_sync
    trigger_dashboard_refresh_sync()
    return new_plans
