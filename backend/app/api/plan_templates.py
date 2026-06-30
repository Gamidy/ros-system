"""PlanTemplate API — 策划模板管理

端点：
- GET    /api/plan-templates?product_type=&market= — 按产品类型和市场获取模板
- POST   /api/plan-templates — 创建模板（require_menu）
- DELETE /api/plan-templates/{id} — 删除模板
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
from app.models.plan_template import PlanTemplate

router = APIRouter(prefix="/plan-templates", tags=["策划模板"])


# ── Schemas ──

class PlanTemplateCreate(BaseModel):
    """创建策划模板请求"""
    product_type: str
    market: str
    name: str
    description: Optional[str] = None
    preset_fields: dict = {}
    is_active: bool = True

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        if v not in VALID_PRODUCT_TYPES:
            raise ValueError(f"不支持的产品类型: {v}")
        return v


class PlanTemplateOut(BaseModel):
    """策划模板输出"""
    id: str
    product_type: str
    market: str
    name: str
    description: Optional[str] = None
    preset_fields: dict
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

@router.get("", response_model=List[PlanTemplateOut])
def list_templates(
    product_type: Optional[str] = None,
    market: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> List[PlanTemplateOut]:
    """按产品类型和市场获取可用模板列表"""
    try:
        query = db.query(PlanTemplate).filter(PlanTemplate.is_active == True)
        if product_type:
            query = query.filter(PlanTemplate.product_type == product_type)
        if market:
            query = query.filter(PlanTemplate.market == market)
        templates: list[PlanTemplate] = query.all()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询模板失败: {str(e)}")


@router.post("", response_model=PlanTemplateOut)
def create_template(
    data: PlanTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> PlanTemplateOut:
    """创建策划模板（管理端）"""
    try:
        template = PlanTemplate(
            product_type=data.product_type,
            market=data.market,
            name=data.name,
            description=data.description,
            preset_fields=data.preset_fields,
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
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)}")


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("product-plans")),
) -> None:
    """删除策划模板"""
    try:
        template = db.query(PlanTemplate).filter(PlanTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        db.delete(template)
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")
