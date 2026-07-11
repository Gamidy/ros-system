from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from uuid import UUID
import uuid

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.models import Material, MaterialCategory, User
from app.schemas import (
    MaterialCreate, MaterialUpdate, MaterialResponse, 
    MaterialListRequest, MaterialListResponse,
    MaterialCategoryCreate, MaterialCategoryUpdate, MaterialCategoryResponse
)

router = APIRouter(prefix="/api/v1/materials", tags=["物料管理"])

@router.get("/categories", response_model=List[MaterialCategoryResponse])
async def list_categories(
    tenant_id: UUID = Query(...),
    parent_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取物料分类列表"""
    query = db.query(MaterialCategory).filter(
        MaterialCategory.tenant_id == tenant_id,
        MaterialCategory.status == "active"
    )
    if parent_id:
        query = query.filter(MaterialCategory.parent_id == parent_id)
    else:
        query = query.filter(MaterialCategory.parent_id.is_(None))
    
    categories = query.order_by(MaterialCategory.sort_order).all()
    
    # 递归构建树形结构
    def build_tree(parent_id=None):
        result = []
        for cat in categories:
            if cat.parent_id == parent_id:
                cat.children = build_tree(cat.id)
                result.append(cat)
        return result
    
    return build_tree(parent_id)

@router.post("/categories", response_model=MaterialCategoryResponse)
async def create_category(
    data: MaterialCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material.create"))
):
    """创建物料分类"""
    # 检查分类编码是否已存在
    existing = db.query(MaterialCategory).filter(
        MaterialCategory.tenant_id == data.tenant_id,
        MaterialCategory.code == data.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="分类编码已存在")
    
    # 计算层级和路径
    level = 1
    path = str(data.code)
    if data.parent_id:
        parent = db.query(MaterialCategory).filter(
            MaterialCategory.id == data.parent_id
        ).first()
        if parent:
            level = parent.level + 1
            path = f"{parent.path}/{data.code}"
    
    category = MaterialCategory(
        **data.model_dump(),
        level=level,
        path=path
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.get("", response_model=MaterialListResponse)
async def list_materials(
    tenant_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    category_id: Optional[UUID] = None,
    part_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取物料列表"""
    query = db.query(Material).filter(
        Material.tenant_id == str(tenant_id),
        Material.deleted_at.is_(None)
    )
    
    if keyword:
        query = query.filter(
            or_(
                Material.part_number.ilike(f"%{keyword}%"),
                Material.part_name.ilike(f"%{keyword}%"),
                Material.specification.ilike(f"%{keyword}%")
            )
        )
    
    if category_id:
        query = query.filter(Material.category_id == category_id)
    if part_type:
        query = query.filter(Material.part_type == part_type)
    if status:
        query = query.filter(Material.status == status)
    
    total = query.count()
    materials = query.order_by(Material.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # 补充关联数据
    result = []
    for material in materials:
        data = MaterialResponse(
            **{k: v for k, v in material.__dict__.items() if not k.startswith('_')}
        )
        if material.category:
            data.category_name = material.category.name
        if material.creator:
            data.creator_name = material.creator.full_name
        result.append(data)
    
    return MaterialListResponse(
        total=total,
        items=result,
        page=page,
        page_size=page_size
    )

@router.post("", response_model=MaterialResponse)
async def create_material(
    data: MaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material.create"))
):
    """创建物料"""
    # 检查物料编码+版本是否已存在
    existing = db.query(Material).filter(
        Material.tenant_id == data.tenant_id,
        Material.part_number == data.part_number,
        Material.version == data.version
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="物料编码+版本已存在")
    
    material = Material(
        **{k: str(v) if isinstance(v, uuid.UUID) else v for k, v in data.model_dump().items()},
        created_by=str(current_user.id)
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    
    response = MaterialResponse(
        **{k: v for k, v in material.__dict__.items() if not k.startswith('_')}
    )
    if material.category:
        response.category_name = material.category.name
    response.creator_name = current_user.full_name
    return response

@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取物料详情"""
    material = db.query(Material).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None)
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    
    response = MaterialResponse(
        **{k: v for k, v in material.__dict__.items() if not k.startswith('_')}
    )
    if material.category:
        response.category_name = material.category.name
    if material.creator:
        response.creator_name = material.creator.full_name
    return response

@router.put("/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: UUID,
    data: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material.edit"))
):
    """更新物料"""
    material = db.query(Material).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None)
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    
    # 已发布的物料不能直接修改，需要走变更流程
    if material.status == "released" and data.status != "obsolete":
        raise HTTPException(
            status_code=400, 
            detail="已发布物料不能直接修改，请通过变更流程处理"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)
    
    material.updated_by = current_user.id
    db.commit()
    db.refresh(material)
    
    response = MaterialResponse(
        **{k: v for k, v in material.__dict__.items() if not k.startswith('_')}
    )
    if material.category:
        response.category_name = material.category.name
    response.creator_name = material.creator.full_name if material.creator else None
    return response

@router.delete("/{material_id}")
async def delete_material(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material.delete"))
):
    """删除物料（软删除）"""
    material = db.query(Material).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None)
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    
    if material.status == "released":
        raise HTTPException(status_code=400, detail="已发布物料不能删除")
    
    material.deleted_at = func.now()
    material.updated_by = current_user.id
    db.commit()
    
    return {"message": "物料已删除"}

@router.post("/{material_id}/release")
async def release_material(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material.edit"))
):
    """发布物料"""
    material = db.query(Material).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None)
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    
    if material.status not in ["draft", "review"]:
        raise HTTPException(status_code=400, detail="当前状态不允许发布")
    
    material.status = "released"
    material.updated_by = current_user.id
    db.commit()
    
    return {"message": "物料已发布", "status": "released"}

@router.post("/{material_id}/revise")
async def revise_material(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("material.create"))
):
    """升版物料"""
    material = db.query(Material).filter(
        Material.id == material_id,
        Material.deleted_at.is_(None)
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    
    if material.status != "released":
        raise HTTPException(status_code=400, detail="只有已发布物料才能升版")
    
    # 解析版本号并升级
    version_parts = material.version.split('.')
    major = version_parts[0]
    minor = int(version_parts[1]) if len(version_parts) > 1 else 1
    new_version = f"{major}.{minor + 1}"
    
    # 创建新版本物料
    new_material = Material(
        tenant_id=material.tenant_id,
        category_id=material.category_id,
        part_number=material.part_number,
        part_name=material.part_name,
        part_type=material.part_type,
        specification=material.specification,
        unit=material.unit,
        version=new_version,
        status="draft",
        lifecycle_phase=material.lifecycle_phase,
        manufacturer=material.manufacturer,
        manufacturer_part_number=material.manufacturer_part_number,
        cost=material.cost,
        weight=material.weight,
        weight_unit=material.weight_unit,
        description=material.description,
        custom_attributes=material.custom_attributes,
        created_by=current_user.id
    )
    db.add(new_material)
    db.commit()
    db.refresh(new_material)
    
    return {"message": "物料已升版", "new_version": new_version, "material_id": new_material.id}
