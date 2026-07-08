"""项目角色→系统岗位映射管理API — 仅admin可操作"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role, get_current_user
from app.models.role_position_mapping import RolePositionMapping

router = APIRouter(prefix="/admin", tags=["admin-role-mappings"])
# PM 脱敏端点路由 — 产品经理等角色可用，仅返回角色名
pm_router = APIRouter(prefix="/pm", tags=["pm-role-mappings"])


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


class RoleMappingPublicOut(BaseModel):
    """脱敏版：仅返回角色名，不暴露内部岗位映射"""
    id: int
    project_role: str

    class Config:
        from_attributes = True


# ── Admin Routes (敏感全量) ──────────────────────────────────────────

@router.get("/role-mappings", response_model=List[RoleMappingOut])
def list_role_mappings(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> list:
    """查询所有角色→岗位映射（仅admin）"""
    return db.query(RolePositionMapping).order_by(RolePositionMapping.id).all()


@router.post("/role-mappings", response_model=RoleMappingOut)
def create_role_mapping(
    data: RoleMappingCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
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
) -> dict:
    """删除角色→岗位映射"""
    mapping = db.query(RolePositionMapping).filter(RolePositionMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(404, "映射不存在")
    db.delete(mapping)
    db.commit()
    return {"ok": True, "id": mapping_id}


# ── PM Routes (脱敏，所有登录用户可读) ───────────────────────────────

@pm_router.get("/role-mappings", response_model=List[RoleMappingPublicOut])
def list_role_mappings_public(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list:
    """查询角色列表（脱敏版：仅返回角色名，所有登录用户可读）"""
    return db.query(RolePositionMapping).order_by(RolePositionMapping.id).all()
