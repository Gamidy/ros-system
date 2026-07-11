from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ==================== 基础模型 ====================

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        populate_by_name = True

# ==================== 认证相关 ====================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserInfo(BaseSchema):
    id: UUID
    username: str
    email: str
    full_name: str
    department: Optional[str] = None
    title: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str

# ==================== 租户 ====================

class TenantBase(BaseSchema):
    code: str
    name: str
    description: Optional[str] = None

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class TenantResponse(TenantBase):
    id: UUID
    status: str
    created_at: datetime

# ==================== 用户 ====================

class UserBase(BaseSchema):
    username: str
    email: EmailStr
    full_name: str
    department: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str
    tenant_id: UUID
    role_ids: Optional[List[UUID]] = []

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    role_ids: Optional[List[UUID]] = None

class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    roles: List[dict] = []

# ==================== 角色权限 ====================

class RoleBase(BaseSchema):
    code: str
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    tenant_id: UUID
    permission_ids: Optional[List[UUID]] = []

class RoleUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[UUID]] = None

class RoleResponse(RoleBase):
    id: UUID
    tenant_id: UUID
    is_system: bool
    created_at: datetime

class PermissionBase(BaseSchema):
    code: str
    name: str
    module: str
    action: str
    description: Optional[str] = None

class PermissionResponse(PermissionBase):
    id: UUID
    created_at: datetime

# ==================== 物料分类 ====================

class MaterialCategoryBase(BaseSchema):
    code: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    sort_order: int = 0

class MaterialCategoryCreate(MaterialCategoryBase):
    tenant_id: UUID

class MaterialCategoryUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    sort_order: Optional[int] = None
    status: Optional[str] = None

class MaterialCategoryResponse(MaterialCategoryBase):
    id: UUID
    tenant_id: UUID
    level: int
    path: Optional[str] = None
    status: str
    created_at: datetime
    children: List['MaterialCategoryResponse'] = []

# ==================== 物料 ====================

class MaterialBase(BaseSchema):
    part_number: str
    part_name: str
    part_type: str = Field(..., pattern="^(raw|component|assembly|finished|semi-finished|tool)$")
    specification: Optional[str] = None
    unit: str = "PCS"
    version: str = "A.1"
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    cost: float = 0
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    description: Optional[str] = None
    custom_attributes: Optional[dict] = None

class MaterialCreate(MaterialBase):
    tenant_id: UUID
    category_id: Optional[UUID] = None

class MaterialUpdate(BaseSchema):
    category_id: Optional[UUID] = None
    part_name: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    cost: Optional[float] = None
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    lifecycle_phase: Optional[str] = None
    custom_attributes: Optional[dict] = None

class MaterialResponse(MaterialBase):
    id: UUID
    tenant_id: UUID
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    status: str
    lifecycle_phase: str
    created_by: UUID
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class MaterialListRequest(BaseSchema):
    page: int = 1
    page_size: int = 20
    keyword: Optional[str] = None
    category_id: Optional[UUID] = None
    part_type: Optional[str] = None
    status: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"

class MaterialListResponse(BaseSchema):
    total: int
    items: List[MaterialResponse]
    page: int
    page_size: int

# ==================== BOM ====================

class BOMItemBase(BaseSchema):
    material_id: UUID
    quantity: float = 1.0
    unit: Optional[str] = None
    reference_designator: Optional[str] = None
    position: Optional[str] = None
    notes: Optional[str] = None
    is_optional: bool = False
    is_substitute_allowed: bool = False
    sort_order: int = 0

class BOMItemCreate(BOMItemBase):
    pass

class BOMItemResponse(BOMItemBase):
    id: UUID
    bom_id: UUID
    material_part_number: Optional[str] = None
    material_part_name: Optional[str] = None
    children: List['BOMItemResponse'] = []
    created_at: datetime

class BOMBase(BaseSchema):
    material_id: UUID
    version: str
    description: Optional[str] = None
    is_default: bool = False
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None

class BOMCreate(BOMBase):
    tenant_id: UUID
    items: List[BOMItemCreate] = []

class BOMUpdate(BaseSchema):
    description: Optional[str] = None
    is_default: Optional[bool] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    items: Optional[List[BOMItemCreate]] = None

class BOMResponse(BOMBase):
    id: UUID
    tenant_id: UUID
    material_part_number: Optional[str] = None
    material_part_name: Optional[str] = None
    status: str
    created_by: UUID
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[BOMItemResponse] = []

# ==================== 变更请求 ====================

class ChangeRequestBase(BaseSchema):
    request_number: str
    title: str
    description: Optional[str] = None
    change_type: str = Field(..., pattern="^(design|process|material|specification|other)$")
    priority: str = "normal"
    target_date: Optional[str] = None
    impact_analysis: Optional[str] = None

class ChangeRequestCreate(ChangeRequestBase):
    tenant_id: UUID
    affected_materials: Optional[List[UUID]] = []
    affected_boms: Optional[List[UUID]] = []
    affected_documents: Optional[List[UUID]] = []

class ChangeRequestUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    target_date: Optional[str] = None
    impact_analysis: Optional[str] = None
    status: Optional[str] = None

class ChangeRequestResponse(ChangeRequestBase):
    id: UUID
    tenant_id: UUID
    status: str
    requested_by: UUID
    requester_name: Optional[str] = None
    requested_date: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ==================== 变更单 ====================

class ChangeOrderItemBase(BaseSchema):
    action_type: str = Field(..., pattern="^(add|remove|modify|replace)$")
    object_type: str = Field(..., pattern="^(material|bom|document|process)$")
    object_id: UUID
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    description: Optional[str] = None

class ChangeOrderBase(BaseSchema):
    order_number: str
    title: str
    description: Optional[str] = None
    change_type: str
    priority: str = "normal"
    target_impl_date: Optional[str] = None

class ChangeOrderCreate(ChangeOrderBase):
    tenant_id: UUID
    change_request_id: Optional[UUID] = None
    items: List[ChangeOrderItemBase] = []

class ChangeOrderResponse(ChangeOrderBase):
    id: UUID
    tenant_id: UUID
    change_request_id: Optional[UUID] = None
    status: str
    planned_by: UUID
    planner_name: Optional[str] = None
    planned_date: Optional[str] = None
    target_impl_date: Optional[str] = None
    actual_impl_date: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[ChangeOrderItemBase] = []

# ==================== 项目 ====================

class ProjectBase(BaseSchema):
    project_code: str
    project_name: str
    description: Optional[str] = None
    project_type: str = "product"
    priority: str = "normal"
    manager_id: Optional[UUID] = None
    start_date: Optional[str] = None
    target_end_date: Optional[str] = None
    budget: Optional[float] = None

class ProjectCreate(ProjectBase):
    tenant_id: UUID

class ProjectUpdate(BaseSchema):
    project_name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    manager_id: Optional[UUID] = None
    start_date: Optional[str] = None
    target_end_date: Optional[str] = None
    budget: Optional[float] = None
    progress: Optional[float] = None

class ProjectResponse(ProjectBase):
    id: UUID
    tenant_id: UUID
    status: str
    progress: float
    manager_name: Optional[str] = None
    created_by: UUID
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProjectTaskBase(BaseSchema):
    task_name: str
    description: Optional[str] = None
    task_type: str = "task"
    priority: str = "normal"
    assigned_to: Optional[UUID] = None
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    estimated_hours: Optional[float] = None

class ProjectTaskCreate(ProjectTaskBase):
    project_id: UUID
    parent_id: Optional[UUID] = None

class ProjectTaskResponse(ProjectTaskBase):
    id: UUID
    project_id: UUID
    parent_id: Optional[UUID] = None
    task_code: Optional[str] = None
    status: str
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    actual_hours: Optional[float] = None
    progress: float
    assignee_name: Optional[str] = None
    created_at: datetime

# ==================== 文档 ====================

class DocumentBase(BaseSchema):
    document_number: str
    document_name: str
    document_type: str
    category: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None

class DocumentCreate(DocumentBase):
    tenant_id: UUID

class DocumentUpdate(BaseSchema):
    document_name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    content: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: UUID
    tenant_id: UUID
    version: str
    status: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_by: UUID
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# 解决循环引用
MaterialCategoryResponse.model_rebuild()
BOMItemResponse.model_rebuild()
