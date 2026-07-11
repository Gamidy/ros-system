"""Phase 2 — ECR API: 工程变更申请接口"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.crud.ecr import ecr_crud
from app.schemas.ecr_eco import (
    ECRCreate, ECRUpdate, ECRRejectRequest, ECRReviewRequest,
    ECRSummaryOut, ECRDetailOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ecr", tags=["ECR"])


@router.post("/", response_model=ECRDetailOut, status_code=status.HTTP_201_CREATED)
async def create_ecr(
    data: ECRCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建 ECR"""
    ecr = await ecr_crud.create(
        db,
        data=data.model_dump(),
        submitter_id=current_user.id,
        submitter_name=current_user.username,
    )
    await db.commit()
    return ecr


@router.get("/", response_model=list[ECRSummaryOut])
async def list_ecrs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    ecr_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出 ECR"""
    return await ecr_crud.list(
        db, skip=skip, limit=limit, status=status, ecr_type=ecr_type
    )


@router.get("/{ecr_id}", response_model=ECRDetailOut)
async def get_ecr(
    ecr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 ECR 详情"""
    ecr = await ecr_crud.get(db, ecr_id)
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    return ecr


@router.put("/{ecr_id}", response_model=ECRDetailOut)
async def update_ecr(
    ecr_id: int,
    data: ECRUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑 ECR（仅 draft 状态）"""
    ecr = await ecr_crud.get(db, ecr_id)
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    try:
        ecr = await ecr_crud.update(db, ecr, data.model_dump(exclude_unset=True))
        await db.commit()
        return ecr
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ecr_id}/submit", response_model=ECRDetailOut)
async def submit_ecr(
    ecr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交 ECR: DRAFT → SUBMITTED"""
    ecr = await ecr_crud.get(db, ecr_id)
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    try:
        ecr = await ecr_crud.submit(db, ecr)
        await db.commit()
        return ecr
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ecr_id}/review", response_model=ECRDetailOut)
async def review_ecr(
    ecr_id: int,
    data: ECRReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批 ECR: SUBMITTED → APPROVED/REJECTED"""
    ecr = await ecr_crud.get(db, ecr_id)
    if not ecr:
        raise HTTPException(status_code=404, detail="ECR 不存在")
    try:
        ecr = await ecr_crud.review(
            db, ecr,
            action=data.action,
            reviewer_id=current_user.id,
            rejection_reason=data.rejection_reason,
        )
        await db.commit()
        return ecr
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
