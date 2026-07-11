"""平台 API — CRUD"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.crud.product import platform_crud
from app.schemas.product import PlatformCreate, PlatformRead

router = APIRouter(prefix="/platforms", tags=["产品平台"])


@router.get("", response_model=list[PlatformRead])
async def list_platforms(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await platform_crud.get_multi(db)


@router.post("", response_model=PlatformRead, status_code=status.HTTP_201_CREATED)
async def create_platform(data: PlatformCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await platform_crud.create(db, obj_in=data.model_dump())


@router.get("/{platform_id}", response_model=PlatformRead)
async def get_platform(platform_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await platform_crud.get(db, platform_id)
    if not obj:
        raise HTTPException(status_code=404, detail="平台不存在")
    return obj


@router.put("/{platform_id}", response_model=PlatformRead)
async def update_platform(platform_id: int, data: PlatformCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await platform_crud.get(db, platform_id)
    if not obj:
        raise HTTPException(status_code=404, detail="平台不存在")
    return await platform_crud.update(db, db_obj=obj, obj_in=data.model_dump())


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(platform_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    ok = await platform_crud.delete(db, id=platform_id)
    if not ok:
        raise HTTPException(status_code=404, detail="平台不存在")
