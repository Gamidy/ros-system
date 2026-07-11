"""物料 + BOM + 特征族 API"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user
from app.crud.bom_feature import material_crud, bom_crud, feature_family_crud
from app.schemas.bom_feature import (
    MaterialCreate, MaterialRead,
    BOMNodeCreate, BOMNodeRead,
    FeatureFamilyCreate, FeatureFamilyRead, FeatureOptionCreate, FeatureOptionRead,
)

materials_router = APIRouter(prefix="/materials", tags=["物料管理"])
bom_router = APIRouter(prefix="/bom", tags=["BOM管理"])
features_router = APIRouter(prefix="/feature-families", tags=["特征族"])


# ── Materials ──
@materials_router.get("", response_model=list[MaterialRead])
async def list_materials(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await material_crud.get_multi(db)


@materials_router.post("", response_model=MaterialRead, status_code=201)
async def create_material(
    data: MaterialCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await material_crud.create(db, obj_in=data.model_dump())


@materials_router.get("/{material_id}", response_model=MaterialRead)
async def get_material(material_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await material_crud.get(db, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="物料不存在")
    return obj


# ── BOM ──
@bom_router.get("", response_model=list[BOMNodeRead])
async def list_bom_nodes(
    model_id: int = Query(..., description="型号ID"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    nodes = await bom_crud.get_tree(db, model_id=model_id)
    return nodes


@bom_router.post("", response_model=BOMNodeRead, status_code=201)
async def create_bom_node(
    data: BOMNodeCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await bom_crud.create(db, obj_in=data.model_dump())


# ── Feature Families ──
@features_router.get("", response_model=list[FeatureFamilyRead])
async def list_features(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await feature_family_crud.get_multi(db)


@features_router.post("", response_model=FeatureFamilyRead, status_code=201)
async def create_feature(data: FeatureFamilyCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await feature_family_crud.create(db, obj_in=data.model_dump())


@features_router.post("/{family_id}/options", response_model=FeatureOptionRead, status_code=status.HTTP_201_CREATED)
async def add_option(family_id: int, data: FeatureOptionCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj_in = data.model_dump()
    obj_in["family_id"] = family_id
    return await feature_family_crud.create_option(db, family_id=family_id, obj_in=obj_in)
