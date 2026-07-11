from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.models import ChangeRequest, ChangeOrder, ChangeOrderItem, User
from app.schemas import (
    ChangeRequestCreate, ChangeRequestUpdate, ChangeRequestResponse,
    ChangeOrderCreate, ChangeOrderResponse, ChangeOrderItemBase
)

router = APIRouter(prefix="/api/v1/changes", tags=["变更管理"])

def generate_request_number(db: Session, tenant_id: UUID) -> str:
    """生成变更请求编号 ECR-YYYY-XXXXX"""
    from datetime import datetime
    year = datetime.now().year
    prefix = f"ECR-{year}-"
    
    # 查询当前年份最大编号
    latest = db.query(ChangeRequest).filter(
        ChangeRequest.tenant_id == tenant_id,
        ChangeRequest.request_number.like(f"{prefix}%")
    ).order_by(ChangeRequest.request_number.desc()).first()
    
    if latest:
        seq = int(latest.request_number.split("-")[-1]) + 1
    else:
        seq = 1
    
    return f"{prefix}{seq:05d}"

def generate_order_number(db: Session, tenant_id: UUID) -> str:
    """生成变更单编号 ECO-YYYY-XXXXX"""
    from datetime import datetime
    year = datetime.now().year
    prefix = f"ECO-{year}-"
    
    latest = db.query(ChangeOrder).filter(
        ChangeOrder.tenant_id == tenant_id,
        ChangeOrder.order_number.like(f"{prefix}%")
    ).order_by(ChangeOrder.order_number.desc()).first()
    
    if latest:
        seq = int(latest.order_number.split("-")[-1]) + 1
    else:
        seq = 1
    
    return f"{prefix}{seq:05d}"

# ==================== 变更请求 (ECR) ====================

@router.get("/requests")
async def list_change_requests(
    tenant_id: UUID,
    status: Optional[str] = None,
    change_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取变更请求列表"""
    query = db.query(ChangeRequest).filter(ChangeRequest.tenant_id == tenant_id)
    
    if status:
        query = query.filter(ChangeRequest.status == status)
    if change_type:
        query = query.filter(ChangeRequest.change_type == change_type)
    
    total = query.count()
    requests = query.order_by(ChangeRequest.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    result = []
    for req in requests:
        data = {
            "id": req.id,
            "tenant_id": req.tenant_id,
            "request_number": req.request_number,
            "title": req.title,
            "description": req.description,
            "change_type": req.change_type,
            "priority": req.priority,
            "status": req.status,
            "requested_by": req.requested_by,
            "requester_name": req.requester.full_name if req.requester else None,
            "requested_date": str(req.requested_date) if req.requested_date else None,
            "target_date": str(req.target_date) if req.target_date else None,
            "created_at": req.created_at,
            "updated_at": req.updated_at
        }
        result.append(data)
    
    return {"total": total, "items": result, "page": page, "page_size": page_size}

@router.post("/requests", response_model=ChangeRequestResponse)
async def create_change_request(
    data: ChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.create"))
):
    """创建变更请求"""
    request_number = generate_request_number(db, data.tenant_id)
    
    req = ChangeRequest(
        tenant_id=data.tenant_id,
        request_number=request_number,
        title=data.title,
        description=data.description,
        change_type=data.change_type,
        priority=data.priority,
        status="draft",
        requested_by=current_user.id,
        target_date=data.target_date,
        impact_analysis=data.impact_analysis,
        affected_materials=data.affected_materials,
        affected_boms=data.affected_boms,
        affected_documents=data.affected_documents
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    
    return ChangeRequestResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        request_number=req.request_number,
        title=req.title,
        description=req.description,
        change_type=req.change_type,
        priority=req.priority,
        status=req.status,
        requested_by=req.requested_by,
        requester_name=current_user.full_name,
        requested_date=str(req.requested_date) if req.requested_date else None,
        target_date=str(req.target_date) if req.target_date else None,
        impact_analysis=req.impact_analysis,
        created_at=req.created_at,
        updated_at=req.updated_at
    )

@router.get("/requests/{request_id}", response_model=ChangeRequestResponse)
async def get_change_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取变更请求详情"""
    req = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="变更请求不存在")
    
    return ChangeRequestResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        request_number=req.request_number,
        title=req.title,
        description=req.description,
        change_type=req.change_type,
        priority=req.priority,
        status=req.status,
        requested_by=req.requested_by,
        requester_name=req.requester.full_name if req.requester else None,
        requested_date=str(req.requested_date) if req.requested_date else None,
        target_date=str(req.target_date) if req.target_date else None,
        impact_analysis=req.impact_analysis,
        created_at=req.created_at,
        updated_at=req.updated_at
    )

@router.put("/requests/{request_id}", response_model=ChangeRequestResponse)
async def update_change_request(
    request_id: UUID,
    data: ChangeRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.create"))
):
    """更新变更请求"""
    req = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="变更请求不存在")
    
    if req.status not in ["draft", "submitted", "reviewing"]:
        raise HTTPException(status_code=400, detail="当前状态不允许修改")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(req, field, value)
    
    db.commit()
    db.refresh(req)
    
    return ChangeRequestResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        request_number=req.request_number,
        title=req.title,
        description=req.description,
        change_type=req.change_type,
        priority=req.priority,
        status=req.status,
        requested_by=req.requested_by,
        requester_name=req.requester.full_name if req.requester else None,
        requested_date=str(req.requested_date) if req.requested_date else None,
        target_date=str(req.target_date) if req.target_date else None,
        impact_analysis=req.impact_analysis,
        created_at=req.created_at,
        updated_at=req.updated_at
    )

@router.post("/requests/{request_id}/submit")
async def submit_change_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.create"))
):
    """提交变更请求审批"""
    req = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="变更请求不存在")
    
    if req.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态可以提交")
    
    req.status = "submitted"
    db.commit()
    
    return {"message": "变更请求已提交", "status": "submitted"}

@router.post("/requests/{request_id}/approve")
async def approve_change_request(
    request_id: UUID,
    comments: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.approve"))
):
    """审批通过变更请求"""
    req = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="变更请求不存在")
    
    if req.status not in ["submitted", "reviewing"]:
        raise HTTPException(status_code=400, detail="当前状态不允许审批")
    
    req.status = "approved"
    db.commit()
    
    return {"message": "变更请求已批准", "status": "approved"}

@router.post("/requests/{request_id}/reject")
async def reject_change_request(
    request_id: UUID,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.approve"))
):
    """拒绝变更请求"""
    req = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="变更请求不存在")
    
    if req.status not in ["submitted", "reviewing"]:
        raise HTTPException(status_code=400, detail="当前状态不允许审批")
    
    req.status = "rejected"
    db.commit()
    
    return {"message": "变更请求已拒绝", "status": "rejected", "reason": reason}

# ==================== 变更单 (ECO) ====================

@router.get("/orders")
async def list_change_orders(
    tenant_id: UUID,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取变更单列表"""
    query = db.query(ChangeOrder).filter(ChangeOrder.tenant_id == tenant_id)
    
    if status:
        query = query.filter(ChangeOrder.status == status)
    
    total = query.count()
    orders = query.order_by(ChangeOrder.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    result = []
    for order in orders:
        data = {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "order_number": order.order_number,
            "change_request_id": order.change_request_id,
            "title": order.title,
            "description": order.description,
            "change_type": order.change_type,
            "priority": order.priority,
            "status": order.status,
            "planned_by": order.planned_by,
            "planner_name": order.planner.full_name if order.planner else None,
            "planned_date": str(order.planned_date) if order.planned_date else None,
            "target_impl_date": str(order.target_impl_date) if order.target_impl_date else None,
            "actual_impl_date": str(order.actual_impl_date) if order.actual_impl_date else None,
            "created_at": order.created_at,
            "updated_at": order.updated_at
        }
        result.append(data)
    
    return {"total": total, "items": result, "page": page, "page_size": page_size}

@router.post("/orders", response_model=ChangeOrderResponse)
async def create_change_order(
    data: ChangeOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.create"))
):
    """创建变更单"""
    order_number = generate_order_number(db, data.tenant_id)
    
    # 如果关联了变更请求，检查请求状态
    if data.change_request_id:
        req = db.query(ChangeRequest).filter(
            ChangeRequest.id == data.change_request_id
        ).first()
        if not req:
            raise HTTPException(status_code=404, detail="关联的变更请求不存在")
        if req.status != "approved":
            raise HTTPException(status_code=400, detail="变更请求未批准，不能创建变更单")
    
    order = ChangeOrder(
        tenant_id=data.tenant_id,
        order_number=order_number,
        change_request_id=data.change_request_id,
        title=data.title,
        description=data.description,
        change_type=data.change_type,
        priority=data.priority,
        status="draft",
        planned_by=current_user.id,
        target_impl_date=data.target_impl_date
    )
    db.add(order)
    db.flush()
    
    # 创建变更单行项目
    for item_data in data.items:
        item = ChangeOrderItem(
            change_order_id=order.id,
            action_type=item_data.action_type,
            object_type=item_data.object_type,
            object_id=item_data.object_id,
            old_value=item_data.old_value,
            new_value=item_data.new_value,
            description=item_data.description
        )
        db.add(item)
    
    db.commit()
    db.refresh(order)
    
    return ChangeOrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        order_number=order.order_number,
        change_request_id=order.change_request_id,
        title=order.title,
        description=order.description,
        change_type=order.change_type,
        priority=order.priority,
        status=order.status,
        planned_by=order.planned_by,
        planner_name=current_user.full_name,
        planned_date=str(order.planned_date) if order.planned_date else None,
        target_impl_date=str(order.target_impl_date) if order.target_impl_date else None,
        actual_impl_date=str(order.actual_impl_date) if order.actual_impl_date else None,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[ChangeOrderItemBase(
            action_type=item.action_type,
            object_type=item.object_type,
            object_id=item.object_id,
            old_value=item.old_value,
            new_value=item.new_value,
            description=item.description
        ) for item in order.items]
    )

@router.get("/orders/{order_id}", response_model=ChangeOrderResponse)
async def get_change_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取变更单详情"""
    order = db.query(ChangeOrder).filter(ChangeOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="变更单不存在")
    
    return ChangeOrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        order_number=order.order_number,
        change_request_id=order.change_request_id,
        title=order.title,
        description=order.description,
        change_type=order.change_type,
        priority=order.priority,
        status=order.status,
        planned_by=order.planned_by,
        planner_name=order.planner.full_name if order.planner else None,
        planned_date=str(order.planned_date) if order.planned_date else None,
        target_impl_date=str(order.target_impl_date) if order.target_impl_date else None,
        actual_impl_date=str(order.actual_impl_date) if order.actual_impl_date else None,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[ChangeOrderItemBase(
            action_type=item.action_type,
            object_type=item.object_type,
            object_id=item.object_id,
            old_value=item.old_value,
            new_value=item.new_value,
            description=item.description
        ) for item in order.items]
    )

@router.post("/orders/{order_id}/submit")
async def submit_change_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.create"))
):
    """提交变更单审批"""
    order = db.query(ChangeOrder).filter(ChangeOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="变更单不存在")
    
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态可以提交")
    
    order.status = "submitted"
    db.commit()
    
    return {"message": "变更单已提交", "status": "submitted"}

@router.post("/orders/{order_id}/approve")
async def approve_change_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.approve"))
):
    """审批通过变更单"""
    order = db.query(ChangeOrder).filter(ChangeOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="变更单不存在")
    
    if order.status not in ["submitted", "reviewing"]:
        raise HTTPException(status_code=400, detail="当前状态不允许审批")
    
    order.status = "approved"
    db.commit()
    
    return {"message": "变更单已批准", "status": "approved"}

@router.post("/orders/{order_id}/implement")
async def implement_change_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("change.approve"))
):
    """实施变更单"""
    from datetime import datetime
    
    order = db.query(ChangeOrder).filter(ChangeOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="变更单不存在")
    
    if order.status != "approved":
        raise HTTPException(status_code=400, detail="变更单未批准，不能实施")
    
    # 实施变更行项目
    for item in order.items:
        if item.status == "pending":
            # 根据action_type执行相应操作
            # 这里简化处理，实际应该调用相应的服务
            item.status = "implemented"
            item.implemented_at = datetime.utcnow()
            item.implemented_by = current_user.id
    
    order.status = "implemented"
    order.actual_impl_date = datetime.utcnow().date()
    order.implementation_notes = f"由 {current_user.full_name} 实施"
    db.commit()
    
    return {"message": "变更单已实施", "status": "implemented"}
