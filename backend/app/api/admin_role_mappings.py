"""项目角色→系统岗位映射管理API — 仅admin可操作"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role, get_current_user
from app.models.role_position_mapping import RolePositionMapping

router = APIRouter(prefix="/api/admin", tags=["admin-role-mappings"])


# ── Request/Response Schemas ──────────────────────────────────────────

class RoleMappingCreate(BaseModel):
    """创建映射请求"""
    project_role: str = Field(..., description="项目角色名, 如'结构工程师'")
    system_role: str = Field(..., description="系统岗位名, 如'主任结构工程师'")


class RoleMappingOut(BaseModel):
    id: int
    project_role: str
    system_role: str

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/role-mappings", response_model=List[RoleMappingOut])
def list_role_mappings(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """查询所有角色→岗位映射（所有登录用户可读）"""
    return db.query(RolePositionMapping).order_by(RolePositionMapping.id).all()


@router.post("/role-mappings", response_model=RoleMappingOut)
def create_role_mapping(
    data: RoleMappingCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """创建角色→岗位映射"""
    mapping = RolePositionMapping(
        project_role=data.project_role,
        system_role=data.system_role,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/role-mappings/{mapping_id}")
def delete_role_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """删除角色→岗位映射"""
    mapping = db.query(RolePositionMapping).filter(RolePositionMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(404, "映射不存在")
    db.delete(mapping)
    db.commit()
    return {"ok": True, "id": mapping_id}
