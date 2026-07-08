"""ReviewTemplate API — 复盘模板管理

端点：
- GET  /api/review-templates?product_type=xxx — 按产品类型获取可用模板
- POST /api/review-templates — 创建模板（管理端）
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, field_serializer, field_validator
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.core.constants import VALID_PRODUCT_TYPES
from app.models.user import User
from app.models.review_template import ReviewTemplate

router = APIRouter(prefix="/review-templates", tags=["复盘模板"])


# ── Schemas ──

class TemplateFieldSchema(BaseModel):
    """模板字段定义"""
    field: str
    label: str
    required: bool = False
    max_length: Optional[int] = None


class TemplateCreate(BaseModel):
    """创建模板请求"""
    product_type: str
    name: str
    template_fields: list[TemplateFieldSchema]
    is_active: bool = True

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        if v not in VALID_PRODUCT_TYPES:
            raise ValueError(f"不支持的产品类型: {v}")
        return v


class TemplateOut(BaseModel):
    """模板输出"""
    id: str
    product_type: str
    name: str
    template_fields: list[TemplateFieldSchema]
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        if v not in VALID_PRODUCT_TYPES:
            raise ValueError(f"不支持的产品类型: {v}")
        return v

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, v: Optional[datetime]) -> Optional[str]:
        return v.isoformat() if v else None

    class Config:
        from_attributes = True


# ── API 端点 ──

@router.get("", response_model=List[TemplateOut])
def list_templates(
    product_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> List[TemplateOut]:
    """按产品类型获取可用模板列表"""
    try:
        query = db.query(ReviewTemplate).filter(ReviewTemplate.is_active == True)
        if product_type:
            query = query.filter(ReviewTemplate.product_type == product_type)
        templates: list[ReviewTemplate] = query.all()
        return templates
    except Exception as e:
        logger.exception("unexpected error")
        raise HTTPException(status_code=500, detail=f"查询模板失败: {str(e)}")


@router.post("", response_model=TemplateOut)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> TemplateOut:
    """创建复盘模板（管理端）"""
    try:
        template = ReviewTemplate(
            product_type=data.product_type,
            name=data.name,
            template_fields=[f.model_dump() for f in data.template_fields],
            is_active=data.is_active,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)}")
    except Exception as e:
        logger.exception("unexpected error")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)}")


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> None:
    """删除复盘模板"""
    try:
        template = db.query(ReviewTemplate).filter(ReviewTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        db.delete(template)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")
