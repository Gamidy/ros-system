"""ProductRequirement API — 产品需求录入（P2需求）

5个端点：
- POST /product-requirements — 提交需求（需登录）
- GET /product-requirements — 需求列表（支持状态筛选+分页）
- GET /product-requirements/{id} — 需求详情
- PUT /product-requirements/{id}/status — 变更状态（accepted/rejected）
- POST /product-requirements/{id}/convert — 转策划草稿
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.models.user import User
from app.models.product_plan import ProductRequirement, ProductPlan, ProductPlanStage
from app.models.product_plan_subs import ProductPlanInitiation

router = APIRouter(prefix="/product-requirements", tags=["产品需求录入"])

# ── Schemas ──


class RequirementCreate(BaseModel):
    """提交需求请求体"""
    market: str = Field(..., min_length=1, max_length=100, description="目标市场")
    customer: Optional[str] = Field(None, max_length=200, description="客户名称")
    contact: Optional[str] = Field(None, max_length=100, description="联系人")
    product_type: str = Field(..., min_length=1, max_length=100, description="产品类型")
    capacity_target: Optional[str] = Field(None, max_length=100, description="目标冷量")
    price_target: Optional[Decimal] = Field(None, description="目标价格")
    energy_standard: Optional[str] = Field(None, max_length=50, description="能效标准")
    sales_volume_forecast: Optional[int] = Field(None, description="年销量预测")
    notes: Optional[str] = Field(None, description="补充说明")
    submitter_name: Optional[str] = Field(None, max_length=100, description="提交人姓名")
    submitter_phone: Optional[str] = Field(None, max_length=20, description="提交人电话")


class RequirementStatusUpdate(BaseModel):
    """变更状态请求体"""
    status: str = Field(..., pattern=r"^(accepted|rejected)$", description="accepted 或 rejected")
    reject_reason: Optional[str] = Field(None, max_length=500, description="拒绝原因（rejected时必须填写）")


class RequirementOut(BaseModel):
    """需求详情响应"""
    id: str
    market: str
    customer: Optional[str] = None
    contact: Optional[str] = None
    product_type: str
    capacity_target: Optional[str] = None
    price_target: Optional[float] = None
    energy_standard: Optional[str] = None
    sales_volume_forecast: Optional[int] = None
    notes: Optional[str] = None
    status: str = "pending"
    reject_reason: Optional[str] = None
    submitter_name: Optional[str] = None
    submitter_phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RequirementConvertResult(BaseModel):
    """转策划草稿响应"""
    plan_id: str
    plan_name: str


class ConvertToPlanResult(BaseModel):
    """需求→策划转换响应（精简版）"""
    plan_id: str
    plan_name: str


class PaginatedRequirements(BaseModel):
    """分页需求列表"""
    items: list[RequirementOut]
    total: int
    page: int
    page_size: int


# ── 辅助函数 ──


def _req_to_dict(req: ProductRequirement) -> dict:
    """将 ProductRequirement ORM 转为响应 dict"""
    return {
        "id": req.id,
        "market": req.market,
        "customer": req.customer,
        "contact": req.contact,
        "product_type": req.product_type,
        "capacity_target": req.capacity_target,
        "price_target": float(req.price_target) if req.price_target else None,
        "energy_standard": req.energy_standard,
        "sales_volume_forecast": req.sales_volume_forecast,
        "notes": req.notes,
        "status": req.status,
        "reject_reason": req.reject_reason,
        "submitter_name": req.submitter_name,
        "submitter_phone": req.submitter_phone,
        "created_at": str(req.created_at) if req.created_at else None,
        "updated_at": str(req.updated_at) if req.updated_at else None,
    }


def _get_requirement_or_404(db: Session, req_id: str) -> ProductRequirement:
    """按ID查找需求，不存在则抛404"""
    req = db.query(ProductRequirement).filter(ProductRequirement.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    return req


# ── API 端点 ──


@router.post("", response_model=RequirementOut, status_code=201)
def create_requirement(
    data: RequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-requirements")),
) -> dict:
    """提交产品需求"""
    try:
        req = ProductRequirement(
            market=data.market,
            customer=data.customer,
            contact=data.contact,
            product_type=data.product_type,
            capacity_target=data.capacity_target,
            price_target=data.price_target,
            energy_standard=data.energy_standard,
            sales_volume_forecast=data.sales_volume_forecast,
            notes=data.notes,
            submitter_name=data.submitter_name or current_user.display_name or current_user.username,
            submitter_phone=data.submitter_phone,
            status="pending",
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        return _req_to_dict(req)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"提交需求失败: {str(e)}")


@router.get("")
def list_requirements(
    status: Optional[str] = Query(None, description="按状态筛选(pending/accepted/converted/rejected)"),
    search: Optional[str] = Query(None, description="模糊搜索市场/客户/产品类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-requirements")),
) -> PaginatedRequirements:
    """需求列表（分页+筛选）"""
    try:
        q = db.query(ProductRequirement)

        if status:
            q = q.filter(ProductRequirement.status == status)
        if search:
            keyword = f"%{search}%"
            q = q.filter(
                ProductRequirement.market.ilike(keyword)
                | ProductRequirement.customer.ilike(keyword)
                | ProductRequirement.product_type.ilike(keyword)
            )

        total = q.count()
        items = (
            q.order_by(ProductRequirement.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [_req_to_dict(r) for r in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"查询需求列表失败: {str(e)}")


@router.get("/{req_id}", response_model=RequirementOut)
def get_requirement_detail(
    req_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-requirements")),
) -> dict:
    """需求详情"""
    req = _get_requirement_or_404(db, req_id)
    return _req_to_dict(req)


@router.put("/{req_id}/status", response_model=RequirementOut)
def update_requirement_status(
    req_id: str,
    data: RequirementStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-requirements")),
) -> dict:
    """变更需求状态（accepted/rejected）"""
    req = _get_requirement_or_404(db, req_id)

    if req.status in ("converted", "rejected"):
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{req.status}」，无法变更"
        )

    if data.status == "rejected" and not data.reject_reason:
        raise HTTPException(status_code=400, detail="拒绝时必须填写拒绝原因")

    if data.status == "rejected":
        req.status = "rejected"
        req.reject_reason = data.reject_reason
    elif data.status == "accepted":
        req.status = "accepted"

    try:
        db.commit()
        db.refresh(req)
        return _req_to_dict(req)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"变更状态失败: {str(e)}")


@router.post("/{req_id}/convert", response_model=RequirementConvertResult)
def convert_requirement_to_plan(
    req_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-requirements")),
) -> dict:
    """将需求转为策划草稿（创建 ProductPlan + 预填 Initiation）"""
    req = _get_requirement_or_404(db, req_id)

    if req.status != "accepted":
        raise HTTPException(
            status_code=400,
            detail=f"仅已采纳(accepted)的需求可转策划，当前状态: {req.status}"
        )

    try:
        # 1. 创建 ProductPlan（DRAFT）
        plan_name = f"{req.product_type}-{req.market}"
        if req.customer:
            plan_name += f"({req.customer})"

        plan = ProductPlan(
            name=plan_name,
            market=req.market,
            status=ProductPlanStage.DRAFT,
            created_by=current_user.username,
        )
        db.add(plan)
        db.flush()

        # 2. 创建 ProductPlanInitiation 预填充字段
        initiation = ProductPlanInitiation(
            product_plan_id=plan.id,
            product_type=req.product_type,
            target_market=req.market,
            customer_name=req.customer,
            energy_rating=req.energy_standard,
            fob_price=str(req.price_target) if req.price_target else None,
            annual_sales_forecast=str(req.sales_volume_forecast) if req.sales_volume_forecast else None,
            # 需求说明存入背景依据
            background_basis=req.notes,
            overall_goal=req.notes,
            other_requirements=req.notes,
        )
        db.add(initiation)

        # 3. 更新需求状态为 converted
        req.status = "converted"

        db.commit()
        db.refresh(plan)
        db.refresh(req)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"转策划失败: {str(e)}")


@router.post("/{req_id}/convert-to-plan", response_model=ConvertToPlanResult)
def convert_requirement_to_plan_v2(
    req_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-requirements")),
) -> dict:
    """需求→策划一键转换（新端点）

    根据需求内容自动创建 ProductPlan 草稿：
    - plan.name = 需求标题（产品类型-市场）
    - 状态设为 DRAFT
    - 创建 ProductPlanInitiation 记录，填入需求中的背景依据/总体目标等信息
    """
    req = _get_requirement_or_404(db, req_id)

    if req.status not in ("accepted", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"仅待处理(pending)或已采纳(accepted)的需求可转策划，当前状态: {req.status}"
        )

    try:
        # 1. 创建 ProductPlan（DRAFT）
        plan_name = f"{req.product_type}-{req.market}"
        if req.customer:
            plan_name += f"({req.customer})"
        if req.notes:
            # 取 notes 前20字作为副标题
            subtitle = req.notes.strip()[:20].replace("\n", " ")
            plan_name = f"{subtitle} - {plan_name}"

        plan = ProductPlan(
            name=plan_name,
            market=req.market,
            status=ProductPlanStage.DRAFT,
            created_by=current_user.username,
        )
        db.add(plan)
        db.flush()

        # 2. 创建 ProductPlanInitiation，填入需求信息
        initiation = ProductPlanInitiation(
            product_plan_id=plan.id,
            product_type=req.product_type,
            target_market=req.market,
            customer_name=req.customer,
            energy_rating=req.energy_standard,
            fob_price=str(req.price_target) if req.price_target else None,
            annual_sales_forecast=str(req.sales_volume_forecast) if req.sales_volume_forecast else None,
            # 需求说明存入背景依据与总体目标
            background_basis=req.notes,
            overall_goal=req.notes,
            other_requirements=req.notes,
        )
        db.add(initiation)

        # 3. 更新需求状态为 converted
        req.status = "converted"

        db.commit()
        db.refresh(plan)
        db.refresh(req)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"转策划失败: {str(e)}")
