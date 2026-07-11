"""系列 + 型号 API — CRUD"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.crud.product import series_crud, model_crud
from app.schemas.product import SeriesCreate, SeriesRead, ModelCreate, ModelRead

# ── Series ──
series_router = APIRouter(prefix="/series", tags=["产品系列"])


@series_router.get("", response_model=list[SeriesRead])
async def list_series(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await series_crud.get_multi(db)


@series_router.post("", response_model=SeriesRead, status_code=201)
async def create_series(data: SeriesCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await series_crud.create(db, obj_in=data.model_dump())


@series_router.get("/{series_id}", response_model=SeriesRead)
async def get_series(series_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await series_crud.get(db, series_id)
    if not obj:
        raise HTTPException(status_code=404, detail="系列不存在")
    return obj


# ── Model ──
model_router = APIRouter(prefix="/models", tags=["产品型号"])


@model_router.get("", response_model=list[ModelRead])
async def list_models(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await model_crud.get_multi(db)


@model_router.post("", response_model=ModelRead, status_code=201)
async def create_model(data: ModelCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await model_crud.create(db, obj_in=data.model_dump())


@model_router.get("/{model_id}", response_model=ModelRead)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await model_crud.get(db, model_id)
    if not obj:
        raise HTTPException(status_code=404, detail="型号不存在")
    return obj
