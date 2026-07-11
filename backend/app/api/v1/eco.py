"""Phase 2 — ECO API: 工程变更指令接口"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.crud.eco import eco_crud
from app.crud.ecr import ecr_crud
from app.schemas.ecr_eco import (
    ECOCreate, ECOUpdate, ECOOut, ECODetailOut, ECOItemCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eco", tags=["ECO"])


@router.post("/", response_model=ECODetailOut, status_code=status.HTTP_201_CREATED)
async def create_eco(
    data: ECOCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建 ECO（可关联已批准的 ECR）"""
    ecr = None
    if data.ecr_id:
        ecr = await ecr_crud.get(db, data.ecr_id)
        if not ecr:
            raise HTTPException(status_code=404, detail="关联的 ECR 不存在")
        if ecr.status != "approved":
            raise HTTPException(status_code=400, detail="只能从已批准的 ECR 创建 ECO")

    eco = await eco_crud.create(
        db, data=data.model_dump(), created_by=current_user.id, ecr=ecr
    )
    await db.commit()
    return eco


@router.get("/", response_model=list[ECOOut])
async def list_ecos(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出 ECO"""
    return await eco_crud.list(db, skip=skip, limit=limit, status=status)


@router.get("/{eco_id}", response_model=ECODetailOut)
async def get_eco(
    eco_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 ECO 详情"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    return eco


@router.put("/{eco_id}", response_model=ECODetailOut)
async def update_eco(
    eco_id: int,
    data: ECOUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑 ECO（仅 draft 状态）"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    try:
        eco = await eco_crud.update(db, eco, data.model_dump(exclude_unset=True))
        await db.commit()
        return eco
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{eco_id}/implement", response_model=ECODetailOut)
async def implement_eco(
    eco_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开始实施 ECO: DRAFT → IMPLEMENTING"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    try:
        eco = await eco_crud.start_implementing(db, eco)
        await db.commit()
        return eco
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{eco_id}/verify", response_model=ECODetailOut)
async def verify_eco(
    eco_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """验证 ECO: IMPLEMENTING → VERIFIED"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    try:
        eco = await eco_crud.verify(db, eco, verified_by=current_user.id)
        await db.commit()
        return eco
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{eco_id}/effect", response_model=ECODetailOut)
async def effect_eco(
    eco_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生效 ECO: VERIFIED → EFFECTIVE"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    try:
        eco = await eco_crud.make_effective(db, eco)
        await db.commit()
        return eco
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{eco_id}/close", response_model=ECODetailOut)
async def close_eco(
    eco_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """关闭 ECO: EFFECTIVE → CLOSED"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    try:
        eco = await eco_crud.close(db, eco, closed_by=current_user.id)
        await db.commit()
        return eco
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{eco_id}/cancel", response_model=ECODetailOut)
async def cancel_eco(
    eco_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消 ECO（任意非终态）"""
    eco = await eco_crud.get(db, eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO 不存在")
    try:
        eco = await eco_crud.cancel(db, eco)
        await db.commit()
        return eco
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
