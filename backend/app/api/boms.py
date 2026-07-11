from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID

from app.database import get_db
from app.core.security import get_current_user, require_permission
from app.models import BOM, BOMItem, Material, User
from app.schemas import (
    BOMCreate, BOMUpdate, BOMResponse, BOMItemCreate, BOMItemResponse
)

router = APIRouter(prefix="/api/v1/boms", tags=["BOM管理"])

def build_bom_tree(items: list, parent_id=None) -> list:
    """递归构建BOM树形结构"""
    result = []
    for item in items:
        if item.parent_item_id == parent_id:
            children = build_bom_tree(items, item.id)
            item.children = children
            result.append(item)
    return result

@router.get("", response_model=list)
async def list_boms(
    tenant_id: UUID,
    material_id: Optional[UUID] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取BOM列表"""
    query = db.query(BOM).filter(BOM.tenant_id == tenant_id)
    
    if material_id:
        query = query.filter(BOM.material_id == material_id)
    if status:
        query = query.filter(BOM.status == status)
    
    total = query.count()
    boms = query.order_by(BOM.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    result = []
    for bom in boms:
        data = {
            "id": bom.id,
            "tenant_id": bom.tenant_id,
            "material_id": bom.material_id,
            "material_part_number": bom.material.part_number if bom.material else None,
            "material_part_name": bom.material.part_name if bom.material else None,
            "version": bom.version,
            "description": bom.description,
            "status": bom.status,
            "is_default": bom.is_default,
            "effective_date": str(bom.effective_date) if bom.effective_date else None,
            "expiry_date": str(bom.expiry_date) if bom.expiry_date else None,
            "created_by": bom.created_by,
            "creator_name": bom.creator.full_name if bom.creator else None,
            "created_at": bom.created_at,
            "updated_at": bom.updated_at,
            "item_count": len(bom.items)
        }
        result.append(data)
    
    return {"total": total, "items": result, "page": page, "page_size": page_size}

@router.post("", response_model=BOMResponse)
async def create_bom(
    data: BOMCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bom.create"))
):
    """创建BOM"""
    # 检查物料是否存在
    material = db.query(Material).filter(
        Material.id == data.material_id,
        Material.deleted_at.is_(None)
    ).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    
    # 检查BOM版本是否已存在
    existing = db.query(BOM).filter(
        BOM.tenant_id == data.tenant_id,
        BOM.material_id == data.material_id,
        BOM.version == data.version
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该物料此版本BOM已存在")
    
    # 创建BOM
    bom = BOM(
        tenant_id=data.tenant_id,
        material_id=data.material_id,
        version=data.version,
        description=data.description,
        is_default=data.is_default,
        effective_date=data.effective_date,
        expiry_date=data.expiry_date,
        created_by=current_user.id
    )
    db.add(bom)
    db.flush()
    
    # 创建BOM行项目
    items = []
    for item_data in data.items:
        # 检查子物料是否存在
        child_material = db.query(Material).filter(
            Material.id == item_data.material_id,
            Material.deleted_at.is_(None)
        ).first()
        if not child_material:
            raise HTTPException(status_code=404, detail=f"子物料不存在: {item_data.material_id}")
        
        # 检查循环引用
        if item_data.material_id == data.material_id:
            raise HTTPException(status_code=400, detail="BOM不能引用自身")
        
        item = BOMItem(
            bom_id=bom.id,
            material_id=item_data.material_id,
            quantity=item_data.quantity,
            unit=item_data.unit or child_material.unit,
            reference_designator=item_data.reference_designator,
            position=item_data.position,
            notes=item_data.notes,
            is_optional=item_data.is_optional,
            is_substitute_allowed=item_data.is_substitute_allowed,
            sort_order=item_data.sort_order
        )
        db.add(item)
        items.append(item)
    
    db.commit()
    db.refresh(bom)
    
    # 构建响应
    items_response = []
    for item in items:
        items_response.append(BOMItemResponse(
            id=item.id,
            bom_id=item.bom_id,
            material_id=item.material_id,
            material_part_number=item.material.part_number if item.material else None,
            material_part_name=item.material.part_name if item.material else None,
            quantity=item.quantity,
            unit=item.unit,
            reference_designator=item.reference_designator,
            position=item.position,
            notes=item.notes,
            is_optional=item.is_optional,
            is_substitute_allowed=item.is_substitute_allowed,
            sort_order=item.sort_order,
            children=[],
            created_at=item.created_at
        ))
    
    return BOMResponse(
        id=bom.id,
        tenant_id=bom.tenant_id,
        material_id=bom.material_id,
        material_part_number=material.part_number,
        material_part_name=material.part_name,
        version=bom.version,
        description=bom.description,
        status=bom.status,
        is_default=bom.is_default,
        effective_date=str(bom.effective_date) if bom.effective_date else None,
        expiry_date=str(bom.expiry_date) if bom.expiry_date else None,
        created_by=bom.created_by,
        creator_name=current_user.full_name,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
        items=items_response
    )

@router.get("/{bom_id}", response_model=BOMResponse)
async def get_bom(
    bom_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取BOM详情（含树形结构）"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    
    # 加载所有行项目
    items = db.query(BOMItem).filter(
        BOMItem.bom_id == bom_id
    ).options(
        joinedload(BOMItem.material)
    ).all()
    
    # 构建树形结构
    def build_tree(parent_id=None):
        result = []
        for item in items:
            if item.parent_item_id == parent_id:
                children = build_tree(item.id)
                item_data = BOMItemResponse(
                    id=item.id,
                    bom_id=item.bom_id,
                    material_id=item.material_id,
                    material_part_number=item.material.part_number if item.material else None,
                    material_part_name=item.material.part_name if item.material else None,
                    quantity=item.quantity,
                    unit=item.unit,
                    reference_designator=item.reference_designator,
                    position=item.position,
                    notes=item.notes,
                    is_optional=item.is_optional,
                    is_substitute_allowed=item.is_substitute_allowed,
                    sort_order=item.sort_order,
                    children=children,
                    created_at=item.created_at
                )
                result.append(item_data)
        return result
    
    tree_items = build_tree()
    
    return BOMResponse(
        id=bom.id,
        tenant_id=bom.tenant_id,
        material_id=bom.material_id,
        material_part_number=bom.material.part_number if bom.material else None,
        material_part_name=bom.material.part_name if bom.material else None,
        version=bom.version,
        description=bom.description,
        status=bom.status,
        is_default=bom.is_default,
        effective_date=str(bom.effective_date) if bom.effective_date else None,
        expiry_date=str(bom.expiry_date) if bom.expiry_date else None,
        created_by=bom.created_by,
        creator_name=bom.creator.full_name if bom.creator else None,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
        items=tree_items
    )

@router.put("/{bom_id}", response_model=BOMResponse)
async def update_bom(
    bom_id: UUID,
    data: BOMUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bom.edit"))
):
    """更新BOM"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    
    if bom.status == "released":
        raise HTTPException(status_code=400, detail="已发布BOM不能直接修改，请创建新版本")
    
    # 更新基本信息
    update_fields = ["description", "is_default", "effective_date", "expiry_date"]
    for field in update_fields:
        value = getattr(data, field, None)
        if value is not None:
            setattr(bom, field, value)
    
    # 如果提供了新的行项目，替换现有行项目
    if data.items is not None:
        # 删除现有行项目
        db.query(BOMItem).filter(BOMItem.bom_id == bom_id).delete()
        
        # 创建新行项目
        for item_data in data.items:
            child_material = db.query(Material).filter(
                Material.id == item_data.material_id,
                Material.deleted_at.is_(None)
            ).first()
            if not child_material:
                raise HTTPException(status_code=404, detail=f"子物料不存在: {item_data.material_id}")
            
            item = BOMItem(
                bom_id=bom.id,
                material_id=item_data.material_id,
                quantity=item_data.quantity,
                unit=item_data.unit or child_material.unit,
                reference_designator=item_data.reference_designator,
                position=item_data.position,
                notes=item_data.notes,
                is_optional=item_data.is_optional,
                is_substitute_allowed=item_data.is_substitute_allowed,
                sort_order=item_data.sort_order
            )
            db.add(item)
    
    bom.updated_by = current_user.id
    db.commit()
    db.refresh(bom)
    
    return await get_bom(bom_id, db, current_user)

@router.delete("/{bom_id}")
async def delete_bom(
    bom_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bom.edit"))
):
    """删除BOM"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    
    if bom.status == "released":
        raise HTTPException(status_code=400, detail="已发布BOM不能删除")
    
    db.delete(bom)
    db.commit()
    
    return {"message": "BOM已删除"}

@router.post("/{bom_id}/release")
async def release_bom(
    bom_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("bom.edit"))
):
    """发布BOM"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    
    if bom.status not in ["draft", "review"]:
        raise HTTPException(status_code=400, detail="当前状态不允许发布")
    
    # 如果设置为默认BOM，取消其他版本的默认设置
    if bom.is_default:
        db.query(BOM).filter(
            BOM.tenant_id == bom.tenant_id,
            BOM.material_id == bom.material_id,
            BOM.id != bom_id
        ).update({"is_default": False})
    
    bom.status = "released"
    bom.updated_by = current_user.id
    db.commit()
    
    return {"message": "BOM已发布", "status": "released"}

@router.get("/{bom_id}/compare/{compare_bom_id}")
async def compare_boms(
    bom_id: UUID,
    compare_bom_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """BOM比较"""
    bom1 = db.query(BOM).filter(BOM.id == bom_id).first()
    bom2 = db.query(BOM).filter(BOM.id == compare_bom_id).first()
    
    if not bom1 or not bom2:
        raise HTTPException(status_code=404, detail="BOM不存在")
    
    items1 = db.query(BOMItem).filter(
        BOMItem.bom_id == bom_id
    ).options(joinedload(BOMItem.material)).all()
    
    items2 = db.query(BOMItem).filter(
        BOMItem.bom_id == compare_bom_id
    ).options(joinedload(BOMItem.material)).all()
    
    # 构建比较结果
    added = []
    removed = []
    modified = []
    unchanged = []
    
    dict1 = {item.material_id: item for item in items1}
    dict2 = {item.material_id: item for item in items2}
    
    for material_id, item in dict1.items():
        if material_id not in dict2:
            removed.append({
                "material_id": material_id,
                "part_number": item.material.part_number if item.material else None,
                "part_name": item.material.part_name if item.material else None,
                "quantity": float(item.quantity),
                "unit": item.unit
            })
        else:
            item2 = dict2[material_id]
            if float(item.quantity) != float(item2.quantity) or item.unit != item2.unit:
                modified.append({
                    "material_id": material_id,
                    "part_number": item.material.part_number if item.material else None,
                    "part_name": item.material.part_name if item.material else None,
                    "old_quantity": float(item.quantity),
                    "new_quantity": float(item2.quantity),
                    "old_unit": item.unit,
                    "new_unit": item2.unit
                })
            else:
                unchanged.append({
                    "material_id": material_id,
                    "part_number": item.material.part_number if item.material else None,
                    "part_name": item.material.part_name if item.material else None,
                    "quantity": float(item.quantity),
                    "unit": item.unit
                })
    
    for material_id, item in dict2.items():
        if material_id not in dict1:
            added.append({
                "material_id": material_id,
                "part_number": item.material.part_number if item.material else None,
                "part_name": item.material.part_name if item.material else None,
                "quantity": float(item.quantity),
                "unit": item.unit
            })
    
    return {
        "bom1": {
            "id": bom1.id,
            "version": bom1.version,
            "material_name": bom1.material.part_name if bom1.material else None
        },
        "bom2": {
            "id": bom2.id,
            "version": bom2.version,
            "material_name": bom2.material.part_name if bom2.material else None
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged
    }

@router.get("/{bom_id}/explode")
async def explode_bom(
    bom_id: UUID,
    level: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """BOM展开（多级展开）"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    
    def get_child_boms(material_id, current_level=1):
        """递归获取子BOM"""
        if current_level > level:
            return []
        
        # 获取物料的默认BOM
        child_bom = db.query(BOM).filter(
            BOM.material_id == material_id,
            BOM.status == "released",
            BOM.is_default == True
        ).first()
        
        if not child_bom:
            return []
        
        items = db.query(BOMItem).filter(
            BOMItem.bom_id == child_bom.id
        ).options(joinedload(BOMItem.material)).all()
        
        result = []
        for item in items:
            item_data = {
                "level": current_level,
                "material_id": item.material_id,
                "part_number": item.material.part_number if item.material else None,
                "part_name": item.material.part_name if item.material else None,
                "quantity": float(item.quantity),
                "unit": item.unit,
                "reference_designator": item.reference_designator,
                "children": get_child_boms(item.material_id, current_level + 1)
            }
            result.append(item_data)
        
        return result
    
    # 获取顶层BOM的行项目
    top_items = db.query(BOMItem).filter(
        BOMItem.bom_id == bom_id
    ).options(joinedload(BOMItem.material)).all()
    
    result = []
    for item in top_items:
        item_data = {
            "level": 0,
            "material_id": item.material_id,
            "part_number": item.material.part_number if item.material else None,
            "part_name": item.material.part_name if item.material else None,
            "quantity": float(item.quantity),
            "unit": item.unit,
            "reference_designator": item.reference_designator,
            "children": get_child_boms(item.material_id, 1)
        }
        result.append(item_data)
    
    return {
        "bom_id": bom_id,
        "bom_version": bom.version,
        "material_name": bom.material.part_name if bom.material else None,
        "max_level": level,
        "items": result
    }
